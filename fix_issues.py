import re

# Fix 1: Update context_retriever.py to add more emphatic time instructions
with open('core/context_retriever.py', 'r', encoding='utf-8') as f:
    context_content = f.read()

old_time_context = '''text = f"**CURRENT TIME CONTEXT:**\\n"
            text += f"Today is {day_name}, {current_date}. Current time is {current_time}.\\n"
            text += f"CRITICAL: Do NOT suggest slots before current time if booking for today!\\n\\n"'''

# Format time in 12-hour for clarity
new_time_context = '''# Format current time in 12-hour for AI clarity
            hour_12 = int(now.strftime("%I"))
            am_pm = now.strftime("%p")
            current_time_12h = f"{hour_12}:{now.strftime('%M')} {am_pm}"
            
            text = f"**CURRENT TIME CONTEXT:**\\n"
            text += f"Today is {day_name}, {current_date}. Current time is {current_time_12h}.\\n"
            text += f"CRITICAL RULES:\\n"
            text += f"- If booking for TODAY, slots must be AFTER {current_time_12h}\\n"
            text += f"- Do NOT book past times like 7:30 PM if current time is 10:00 PM\\n"
            text += f"- Clinic closes at 8 PM typically - no evening appointments after 7 PM if it's night\\n\\n"'''

if old_time_context in context_content:
    context_content = context_content.replace(old_time_context, new_time_context)
    print('Fix 1: Updated context_retriever with emphatic time rules')
else:
    print('Fix 1: Context time pattern not found')

with open('core/context_retriever.py', 'w', encoding='utf-8') as f:
    f.write(context_content)

# Fix 2: Update realtime_client.py prompt for end-call greeting
with open('core/realtime_client.py', 'r', encoding='utf-8') as f:
    realtime_content = f.read()

old_end_call = '''6. BEFORE ending the call:
           - Ask: "Is there anything else I can help you with?" or "Inkemina help kavala?"
           - Wait for their response
           - ONLY after they confirm NO more queries, say goodbye and use end_call tool
           - Never hang up abruptly without asking if they need more help'''

new_end_call = '''6. ENDING THE CALL (FOLLOW THIS EXACTLY):
           - First ask: "Inkemina help kavala?" or "Is there anything else?"
           - Wait for their response
           - When they say no/bye/done:
             1. Say a warm goodbye: "Thank you for calling! Have a great day!" 
             2. THEN call the end_call tool
           - NEVER hang up without saying goodbye first!'''

if old_end_call in realtime_content:
    realtime_content = realtime_content.replace(old_end_call, new_end_call)
    print('Fix 2: Updated end-call instructions with explicit greeting')
else:
    print('Fix 2: End-call pattern not found')

with open('core/realtime_client.py', 'w', encoding='utf-8') as f:
    f.write(realtime_content)

print('All fixes applied!')
