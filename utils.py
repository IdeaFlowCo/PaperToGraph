from datetime import datetime
import json


def log_msg(msg:str):
    '''
    Log provided message in a standardized way.
    '''
    ts = datetime.now().isoformat(timespec='seconds')
    print(f'[{ts}] {msg}')


def clean_json(response):
    cleaned = {}
    try:
        if response.startswith('Output:'):
            # Remove extraneous "Output:" signifier that shows up sometimes.
            response = response[len('Output:'):].strip()
        response_dict = json.loads(response)
        for key, value in response_dict.items():
            # We want to skip the empty values to avoid overloading GPT in subsequent queries.
            if not value:
                continue
            if isinstance(value, dict):
                cleaned_value = {}
                # Sometimes a dict will have a bunch of key => empty dict pairs inside of it for some reason?
                # Trim those too.
                for subkey, subvalue in value.items():
                    if subvalue:
                        cleaned_value[subkey] = subvalue
                # Check that the cleaned up value dict actually has anything in it; if not, skip
                if not cleaned_value:
                    continue
                value = cleaned_value
            else:
                # Sometimes we get really long string pairs that are more trouble than they are informative
                if len(key) + len(value) > 200:
                    continue
            cleaned[key] = value
        cleaned = json.dumps(cleaned, indent=2)
        log_msg(f'Cleaned up response JSON: \n{cleaned}')
        return cleaned
    except json.decoder.JSONDecodeError:
        log_msg('Response not valid JSON!')
        if '{' in response:
            # Response isn't valid JSON but may be close enough that it can still be used, so we'll just return it as-is
            return response
        return None
