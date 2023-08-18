import json

import boto3

from .common import fetch_response


DATA_PREP_SM_TEMPLATE = (
    'In the user message, there will be an extract from a scientific paper. '
    'Generate a series of questions and answers about the content in the extract that could be used to train an LLM. '
    'Answers must be tuples separated by newline of the form ("question", "answer"). '
    # "In the user message, there will be an extract from a scientific paper. Perform the following steps:"
    # '\n'
    # '\n1. Generate a series of questions and answers about the content in the extract that could be used to train an LLM.'
    # '\n2. List each question and answer in a ("question", "answer") tuple. '
    # 'Make sure there are quotes around each question and answer. '
    # 'Also make sure that each tuple is on its own line, and that the question always comes first in the tuple.'
    # '\n\n'
    # 'For example, if the provided input is: "{sample_input}", an output could look like this:'
    # '\n'
    # '\n```\n'
    # '{sample_output}'
    # '\n```\n'
)
SAMPLE_DATA_PREP_INPUT = (
    "Hypophosphatasia (HP) (MIM 241510) is an inborn error of bone metabolism, characterized by a genetic "
    "defect in the gene encoding the tissue-nonspecific alkaline phosphatase (TNSALP)."
)
SAMPLE_DATA_PREP_OUTPUT = (
    '("What is Hypophosphatasia?", "Hypophosphatasia is an inborn error of bone metabolism.")\n'
    '("What is Hypophosphatasia characterized by?", "Hypophosphatasia is characterized by a genetic defect in the gene '
    'encoding the tissue-nonspecific alkaline phosphatase (TNSALP).")'
)

DATA_PREP_SYSTEM_MESSAGE = {
    'role': 'system',
    # "content": DATA_PREP_SM_TEMPLATE.format(sample_input=SAMPLE_DATA_PREP_INPUT, sample_output=SAMPLE_DATA_PREP_OUTPUT)
    'content': DATA_PREP_SM_TEMPLATE
}


def test_run():
    dialogs = [
        [{"role": "user", "content": "what is the recipe of mayonnaise?"}],
        [
            {"role": "user", "content": "I am going to Paris, what should I see?"},
            {
                "role": "assistant",
                "content": """\
    Paris, the capital of France, is known for its stunning architecture, art museums, historical landmarks, and romantic atmosphere. Here are some of the top attractions to see in Paris:

    1. The Eiffel Tower: The iconic Eiffel Tower is one of the most recognizable landmarks in the world and offers breathtaking views of the city.
    2. The Louvre Museum: The Louvre is one of the world's largest and most famous museums, housing an impressive collection of art and artifacts, including the Mona Lisa.
    3. Notre-Dame Cathedral: This beautiful cathedral is one of the most famous landmarks in Paris and is known for its Gothic architecture and stunning stained glass windows.

    These are just a few of the many attractions that Paris has to offer. With so much to see and do, it's no wonder that Paris is one of the most popular tourist destinations in the world.""",
            },
            {"role": "user", "content": "What is so great about #1?"},
        ],
        [
            {"role": "system", "content": "Always answer with Haiku"},
            {"role": "user", "content": "I am going to Paris, what should I see?"},
        ],
        [
            {
                "role": "system",
                "content": "Always answer with emojis",
            },
            {"role": "user", "content": "How to go from Beijing to NY?"},
        ],
    ]
    for dialog in dialogs:
        payload = {
            "inputs": [dialog],
            "parameters": {"max_new_tokens": 1024, "top_p": 0.9, "temperature": 0.3}
        }
        result = fetch_response(payload)[0]
        for msg in dialog:
            print(f"{msg['role'].capitalize()}: {msg['content']}\n")
        print(f"> {result['generation']['role'].capitalize()}: {result['generation']['content']}")
        print("\n==================================\n")


TEST_INPUT = (
    'Aneurysms are characterized by structural deterioration of the vascular wall leading to progressive '
    'dilatation and, potentially, rupture of the aorta. While aortic aneurysms often remain clinically '
    'silent, the morbidity and mortality associated with aneurysm expansion and rupture are considerable. Over '
    '13,000 deaths annually in the United States are attributable to aortic aneurysm rupture with less than '
    '1 in 3 persons with aortic aneurysm rupture surviving to surgical intervention. Environmental and epidemiologic '
    'risk factors including smoking, male gender, hypertension, older age, dyslipidemia, atherosclerosis, and '
    'family history are highly associated with abdominal aortic aneurysms, while heritable genetic mutations are '
    'commonly associated with aneurysms of the thoracic aorta. Similar to other forms of cardiovascular disease, '
    'family history, genetic variation, and heritable mutations modify the risk of aortic aneurysm formation and '
    'provide mechanistic insight into the pathogenesis of human aortic aneurysms. This review will examine the '
    'relationship between heritable genetic and epigenetic influences on thoracic and abdominal aortic aneurysm '
    'formation and rupture.'
)


def test_data_prep():
    dialog = [
        DATA_PREP_SYSTEM_MESSAGE,
        {
            'role': 'user',
            'content': TEST_INPUT,
        }
    ]
    payload = {
        "inputs": [dialog],
        "parameters": {"max_new_tokens": 256, "top_p": 0.9, "temperature": 0.6}
    }
    result = fetch_response(payload)
    print(result)
    result = result[0]
    print(result['generation']['content'])


def main():
    payloads = [
        # {
        #     "inputs": ['What is Hypophosphatasia?'],
        #     "parameters": {"max_new_tokens": 256, "top_p": 0.9, "temperature": 0.2, "return_full_text": False, 'stop_sequence': '\n'}
        # },
        # {
        #     "inputs": ['What is Ehlers-Danlos Syndrome?'],
        #     "parameters": {"max_new_tokens": 256, "top_p": 0.9, "temperature": 0.2, "return_full_text": False, 'stop_sequence': ['\n']}
        # },
        # {
        #     "inputs": ['What is TNXB EDS?'],
        #     "parameters": {"max_new_tokens": 256, "top_p": 0.9, "temperature": 0.2, "return_full_text": False, 'stop_sequence': ['\n']}
        # },
        {
            "inputs": ['What are some connections between Ehlers-Danlos Syndrome and Hypophosphatasia?'],
            "parameters": {"max_new_tokens": 256, "top_p": 0.90, "temperature": 0.2, "return_full_text": False, 'stop_sequence': ['\n']}
        },
    ]
    for payload in payloads:
        query_response = fetch_response(payload)
        print(payload["inputs"])
        response = query_response[0]['generation']  # .split('\n')[1]
        print(f"> {response}")
        print("\n==================================\n")


if __name__ == '__main__':
    main()
