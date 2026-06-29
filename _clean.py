import re, os

base = 'D:\\shusousou\\shusousou'
files = [
    base + '\\main.py',
    base + '\\modules\\auth\\routes.py', 
    base + '\\templates\\base.html',
    base + '\\config.py'
]

for fp in files:
    with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # 用更灵活的正则
    content = re.sub(r'<<<<<<< HEAD[\s\S]*?=======\n?', '', content)
    content = re.sub(r'>>>>>>> [^\n]*\n?', '', content)
    
    # routes.py 特殊处理：login_register.html -> register.html
    content = content.replace('\"login_register.html\"', '\"register.html\"')
    
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f'OK: {fp}')

print('完成')
