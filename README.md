## NVC API

**Summary**: Simple Flask API for recognizing entities in freeform text using your choice of GPT model.

**Steps**: pip install Flask, pip install openai, set openai api key in app.py, run python3 app.py

Install all dependencies for first time set up:
`pip3 install -r requirements.txt`

To add api key locally, set environment variable in your shell:
`export OPENAI_API_KEY=sk-API-KEY-HERE`
from https://platform.openai.com/account/api-keys

Then, to run locally, pass `--local` flag:
`python app.py --local`

