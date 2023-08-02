
import asyncio
import json

from quart import make_response

from .logging import log_msg


async def gen_result_with_heartbeat(work_fn, log_label='function', heartbeat_interval=10):
    '''
    Call work_fn, periodically yielding ' ' as a heartbeat until work_fn completes.

    If work_fn returns a non-string value, the result will be converted using json.dumps before being yielded.
    '''
    yield ' '
    work_task = asyncio.create_task(work_fn)
    while True:
        try:
            await asyncio.wait([work_task], timeout=heartbeat_interval, return_when=asyncio.FIRST_COMPLETED)
            if work_task.cancelled():
                log_msg(f'{log_label} task cancelled, exiting gen_result loop')
                break
            elif work_task.done():
                result = work_task.result()
                if not isinstance(result, str):
                    result = json.dumps(result)
                yield result
                break
            else:
                log_msg(f'{log_label} still running, yielding connection heartbeat')
                yield ' '
                heartbeat_task = asyncio.create_task(asyncio.sleep(heartbeat_interval))
        except asyncio.CancelledError:
            log_msg(f'Client disconnected, cancelling {log_label} task')
            work_task.cancel()
            heartbeat_task.cancel()


async def make_response_with_heartbeat(work_fn, log_label='function', heartbeat_interval=10):
    result_generator = gen_result_with_heartbeat(
        work_fn,
        log_label=log_label,
        heartbeat_interval=heartbeat_interval
    )
    response = await make_response(
        result_generator,
        {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache',
            'Transfer-Encoding': 'chunked',
        },
    )
    response.timeout = None
    return response
