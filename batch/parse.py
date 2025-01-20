import asyncio
import json
import os
import tempfile

import aws
import gpt
import parse
import utils
from utils import doc_convert, log_msg


class BatchParseJob:
    def __init__(
        self, gpt_model=None, dry_run=False, prompt_override=None, log_file=None
    ):
        self.gpt_model = gpt.sanitize_gpt_model_choice(gpt_model)
        self.dry_run = dry_run
        self.prompt_override = prompt_override
        self.log_file = log_file
        # Will be set by run() when output folder is created
        self.job_output_uri = None
        # Will be filled with tasks writing output files to S3
        self.output_tasks = set()

    async def __find_input_files(self, data_source):
        files = aws.get_objects_at_s3_uri(data_source)
        if not files:
            raise Exception(f"No files found at {data_source}")

        log_msg(f"Found {len(files)} files to process")
        log_msg(files)
        return files

    async def __fetch_input_file(self, file_uri):
        log_msg(f"Fetching file {file_uri}")
        file_name, data = aws.read_file_from_s3(file_uri)
        log_msg(f"Loaded {len(data)} bytes")

        # If file is PDF or other document format, convert it to text
        if isinstance(data, bytes) and file_name.lower().endswith(
            (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx")
        ):
            with tempfile.NamedTemporaryFile(
                suffix=os.path.splitext(file_name)[1], delete=False
            ) as temp_file:
                temp_file.write(data)  # Write raw bytes directly
                temp_path = temp_file.name
            try:
                data = doc_convert.convert_to_text(temp_path)
                log_msg(f"Converted document to {len(data)} bytes of text")
            finally:
                os.unlink(temp_path)  # Clean up temp file

        return file_name, data

    async def __process_file(self, file_uri):
        try:
            input_file_name, input_data = await self.__fetch_input_file(file_uri)

            # At this point input_data should be text, either from a text file or converted from a document
            if not isinstance(input_data, str):
                log_msg(f"Could not convert file {file_uri} to text. Skipping.")
                return

        except Exception as e:
            log_msg(f"Error processing file {file_uri}: {e}")
            return

        file_output_uri = aws.create_output_dir_for_file(
            self.job_output_uri, input_file_name, dry_run=self.dry_run
        )

        await self.__copy_input_file_to_output_folder(
            input_file_name, input_data, file_output_uri
        )

        log_msg(f"Beginning parse of file: {input_file_name}")
        parse_multitask = parse.parse_with_gpt_multitask(
            input_data, model=self.gpt_model, prompt_override=self.prompt_override
        )
        output_num = 0
        async for parse_input, parse_result in parse_multitask:
            output_num += 1
            # Create a task for each output chunk so that we can write them in parallel
            task = asyncio.create_task(
                self.__write_output_for_file_chunk(
                    parse_input, parse_result, file_output_uri, output_num
                )
            )
            self.output_tasks.add(task)
            task.add_done_callback(self.output_tasks.discard)

    async def __write_output_for_file_chunk(
        self, input_chunk, output_data, file_output_uri, output_num
    ):
        input_chunk_uri = (
            f"{file_output_uri.rstrip('/')}/output_{output_num}.source.txt"
        )
        log_msg(f"Writing input chunk {output_num} to {input_chunk_uri}")
        if self.dry_run:
            log_msg(f"Would have written {len(input_chunk)} bytes")
        else:
            aws.write_to_s3_file(input_chunk_uri, input_chunk)

        output_chunk_uri = f"{file_output_uri.rstrip('/')}/output_{output_num}.json"
        log_msg(f"Writing output chunk {output_num} to {output_chunk_uri}")
        if self.dry_run:
            log_msg(f"Would have written {len(output_data)} bytes")
        else:
            aws.write_to_s3_file(output_chunk_uri, output_data)

    async def __copy_input_file_to_output_folder(
        self, input_name, input_data, output_folder_uri
    ):
        log_msg(
            f"Writing copy of input file {input_name} to output folder {output_folder_uri}"
        )
        if self.dry_run:
            log_msg(f"Would have written {len(input_data)} bytes")
            return

        copied_file_uri = f"{output_folder_uri.rstrip('/')}/source.txt"
        aws.write_to_s3_file(copied_file_uri, input_data)

    async def __write_job_args_to_output_folder(self, data_source, output_uri_arg):
        job_args_uri = f"{self.job_output_uri}/job_args.json"
        if self.dry_run:
            log_msg(f"Would have written job args to {job_args_uri}")
            return

        if self.prompt_override:
            parse_prompt = self.prompt_override
        else:
            parse_prompt = gpt.get_default_parse_prompt()

        job_args = {
            "data_source": data_source,
            "output_uri": output_uri_arg,
            "gpt_model": self.gpt_model,
            "parse_prompt": parse_prompt,
        }
        job_args = json.dumps(job_args, indent=2)
        aws.write_to_s3_file(job_args_uri, job_args)

    async def __upload_log_file(self):
        if not self.log_file:
            return

        log_file_uri = f"{self.job_output_uri}/job_log.txt"

        if self.dry_run:
            log_msg(f"Would have uploaded job log file to {log_file_uri}")
        else:
            log_msg(f"Uploading job log file to {log_file_uri}")
            aws.upload_to_s3(log_file_uri, self.log_file)

    async def run(self, data_source, output_uri):
        # Standardize on s3:// URIs within batch code.
        data_source = aws.http_to_s3_uri(data_source)
        output_uri = aws.http_to_s3_uri(output_uri)

        log_msg(
            f"Beginning parse job for {data_source} using GPT model {self.gpt_model}"
        )

        # Gather input files first so that we can fail fast if there are any issues doing so.
        input_files = await self.__find_input_files(data_source)

        self.job_output_uri = aws.create_output_dir_for_job(
            data_source, output_uri, dry_run=self.dry_run
        ).rstrip("/")

        # Preserve this job's args in the output folder for any future investigations.
        await self.__write_job_args_to_output_folder(data_source, output_uri)

        try:
            for i, input_file in enumerate(input_files):
                log_msg(
                    f"********* Processing file {input_file} ({i + 1} out of {len(input_files)})"
                )
                await self.__process_file(input_file)

            # Wait for all output tasks to complete before exiting.
            await asyncio.gather(*self.output_tasks)
            log_msg("All output tasks complete.")

            log_msg(f"All parsing complete.")
            log_msg(f"Output URI: {self.job_output_uri}")
        finally:
            # Make sure we upload the log file even if there's an exception during processing.
            await self.__upload_log_file()
