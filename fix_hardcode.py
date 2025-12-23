with open('core/context_retriever.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove the hardcoded 8 PM line
old_line = "text += f\"- Clinic closes at 8 PM typically - no evening appointments after 7 PM if it's night\\n\\n\""
new_line = "text += f\"- Check CLINIC HOURS section below for actual closing time\\n\\n\""

if old_line in content:
    content = content.replace(old_line, new_line)
    print('Removed hardcoded 8 PM, now references dynamic clinic hours')
else:
    print('Pattern not found')

with open('core/context_retriever.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done!')
