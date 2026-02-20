import os

output_dir = "/Users/chenyiyun/PycharmProjects/Ranking/output"

print("=" * 60)
print("输出文件列表：")
print("=" * 60)

for filename in sorted(os.listdir(output_dir)):
    if filename.endswith(('.csv', '.md')):
        filepath = os.path.join(output_dir, filename)
        size = os.path.getsize(filepath)
        print(f"\n📄 {filename} ({size} bytes)")
        
        # 如果是 CSV 文件，显示前 5 行
        if filename.endswith('.csv'):
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()[:6]
                for i, line in enumerate(lines):
                    if i == 0:
                        print("   " + line.strip())
                    else:
                        print("   " + line.strip())
        
        # 如果是 MD 文件，显示前几行
        elif filename.endswith('.md'):
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()[:10]
                for line in lines[:5]:
                    print("   " + line.rstrip())
