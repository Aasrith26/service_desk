import sounddevice as sd

devs = sd.query_devices()
for i, d in enumerate(devs):
    if isinstance(d, dict):
        name = d.get('name', 'unknown')
        in_ch = d.get('max_input_channels', 0)
        out_ch = d.get('max_output_channels', 0)
        default_in = ' [DEFAULT INPUT]' if i == sd.default.device[0] else ''
        print(f'{i}: {name} - Input:{in_ch}, Output:{out_ch}{default_in}')

print(f'\nDefault input device: {sd.default.device[0]}')
print(f'Default output device: {sd.default.device[1]}')
