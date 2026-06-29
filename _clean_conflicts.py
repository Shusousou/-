import re

files = [
    'shusousou/main.py',
    'shusousou/modules/auth/routes.py',
    'shusousou/templates/base.html',
    'shusousou/config.py'
]

for fp in files:
    with open(fp, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 移除所有冲突标记
    content = re.sub(r'<<<<<<< HEAD\n?', '', content)
    content = re.sub(r'\n?=======\n?', '\n', content)
    content = re.sub(r'\n?>>>>>>> origin/main\n?', '\n', content)
    content = re.sub(r'\n?>>>>>>> e499ee1.*?\n?', '\n', content)
    
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f'已清理: {fp}')

print('全部完成')
