import argparse
import asyncio

import aws
import parse
import utils
from utils import log_msg


class BatchParseJob:
    def __init__(self, gpt_model=None, dry_run=False, prompt_override=None):
        self.gpt_model = utils.sanitize_gpt_model_choice(gpt_model)
        self.dry_run = dry_run
        self.prompt_override = prompt_override

    async def __find_input_files(self, data_source):
        files = aws.get_objects_at_s3_uri(data_source)
        if not files:
            raise Exception(f'No files found at {data_source}')

        log_msg(f'Found {len(files)} files to process')
        log_msg(files)
        return files


    async def __fetch_input_file(self, file_uri):
        log_msg(f'Fetching file {file_uri}')
        file_name, data = aws.read_file_from_s3(file_uri)
        log_msg(f'Loaded {len(data)} bytes')
        return file_name, data


    async def __process_file(self, file_uri, job_output_uri):
        try:
            input_file_name, input_data = await self.__fetch_input_file(file_uri)
        except UnicodeDecodeError:
            log_msg(f'Could not decode file {file_uri} as UTF-8. Skipping.')
            return

        file_output_uri = aws.create_output_dir_for_file(job_output_uri, input_file_name, dry_run=self.dry_run)

        await self.__copy_input_file_to_output_folder(input_file_name, input_data, file_output_uri)

        log_msg(f'Beginning parse of file: {input_file_name}')
        output_num = 0
        async for parse_result in parse.parse_with_gpt_multitask(input_data, model=self.gpt_model, prompt_override=self.prompt_override):
            # Create a task for each output chunk so that we can write them in parallel
            asyncio.create_task(
                self.__write_output_for_file_chunk(
                    parse_result, 
                    file_output_uri,
                    output_num))
            output_num += 1


    async def __write_output_for_file_chunk(self, output_data, file_output_uri, output_num):
        output_chunk_uri = f'{file_output_uri.rstrip("/")}/output_{output_num}.json'
        log_msg(f'Writing output chunk {output_num} to {output_chunk_uri}')

        if self.dry_run:
            log_msg(f'Would have written {len(output_data)} bytes')
            return

        aws.write_file_to_s3(output_chunk_uri, output_data)


    async def __copy_input_file_to_output_folder(self, input_name, input_data, output_folder_uri):
        log_msg(f'Writing copy of input file {input_name} to output folder {output_folder_uri}')
        if self.dry_run:
            log_msg(f'Would have written {len(input_data)} bytes')
            return

        copied_file_uri = f'{output_folder_uri.rstrip("/")}/source.txt'
        aws.write_file_to_s3(copied_file_uri, input_data)


    async def run(self, data_source, output_uri):
        log_msg(f'Beginning parse job for {data_source} using GPT model {self.gpt_model}')
        input_files = await self.__find_input_files(data_source)
        job_output_uri = aws.create_output_dir_for_job(data_source, output_uri, dry_run=self.dry_run)
        for i, input_file in enumerate(input_files):
            log_msg(f'********* Processing file {input_file} ({i+1} out of {len(input_files)})')
            await self.__process_file(input_file, job_output_uri)




if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--data_source',
        default='s3://paper2graph-parse-inputs',
        help="The URI for the text to be parsed, like an S3 bucket location."
    )
    parser.add_argument(
        '--output_uri',
        default='s3://paper2graph-parse-results',
        help="The URI where output is saved, like an S3 bucket location."
    )
    parser.add_argument(
        '--gpt_model',
        default='gpt-3.5-turbo',
        help="The GPT model to use when parsing."
    )
    parser.add_argument(
        '--dry_run',
        action="store_true",
        default=False, 
        help="The URI where output is saved, like an S3 bucket location."
    )
    args = parser.parse_args()

    parse_job = BatchParseJob(gpt_model=args.gpt_model, dry_run=args.dry_run)

    asyncio.run(
        parse_job.run(args.data_source, args.output_uri)
    )
