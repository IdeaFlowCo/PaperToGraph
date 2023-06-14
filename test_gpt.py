import gpt

print('***************')
print('GPT prompt info')
print('***************')
print()
print('Parse prompt as will be sent in system message:')
print('\n*****')
print(gpt.parse.PARSE_SYSTEM_MESSAGE['content'])
print('*****\n\n\n')
print('Merge prompt as will be sent in system message:')
print('\n*****')
print(gpt.merge.MERGE_SYSTEM_MESSAGE['content'])
print('*****')
