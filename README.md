## NVC API

**Summary**: Simple Flask API for recognizing entities in freeform text using your choice of GPT model.

**Steps**: pip install requirements, set openai api key, run python3 app.py

Install all dependencies for first time set up:
`pip3 install -r requirements.txt`

To add api key locally, set environment variable in your shell:
`export OPENAI_API_KEY=sk-API-KEY-HERE`
from https://platform.openai.com/account/api-keys

Then, to run locally, pass `--local` flag:
`python3 app.py --local`

**Virtual environment**:

It's highly recommended you run the app using a virtual environment to make dependency management easy.

If the environment is named `venv` it will be picked up by VS Code etc and the local environment files will be ignored by git.

To create: 
`python3 -m venv venv`

To activate:
`source venv/bin/activate`

Your shell prompt should change to reflect the new environment:

```
Before:
someone@somewhere:~/Code/IdeaflowEntityExtractor$

After:
(venv) someone@somewhere:~/Code/IdeaflowEntityExtractor$
```
