## Paper2Graph Entity Extractor

**Summary**: Simple Quart server for recognizing entities in freeform text using your choice of GPT model.

**Steps**: pip install requirements, set openai api key, run python3 app.py

Install all dependencies for first time set up:
`pip3 install -r requirements.txt`

To add api key locally, set environment variable in your shell:
`export OPENAI_API_KEY=sk-API-KEY-HERE`
from https://platform.openai.com/account/api-keys

To interact with S3 for various functionality, make sure `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are set
in your environment variables. If you're logged in with the AWS CLI, you can simply run the following commands to grab
those keys from your default profile:
```
export AWS_ACCESS_KEY_ID=`aws configure get default.aws_access_key_id`
export AWS_SECRET_ACCESS_KEY=`aws configure get default.aws_secret_access_key`
```

To run the app with the Quart dev server (instead of routing through a separate `hypercorn` instance),
set the `P2G_DEV_SERVER` environment variable:
`P2G_DEV_SERVER=True python3 app.py`

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
