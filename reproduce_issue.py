
# Simulate app.py logic

# Mock CLUB_MAP
CLUBS = [
    {'name': 'D.N.A.', 'code': 'DN'},
    {'name': 'Crowwood', 'code': 'CW'},
    {'name': 'Stirling', 'code': 'ST'}
]
CLUB_MAP = {c['code']: c['name'] for c in CLUBS}

# Mock Player Result
match = {
    'name': 'Test Player',
    'club': 'DN, CW'  # This is what chess_grading.py returns
}

# app.py logic (NEW)
row = match.copy()
c_code_raw = row.get('club', '')
c_parts = [c.strip() for c in c_code_raw.split(',') if c.strip()]
c_display_parts = []

for code in c_parts:
    if code in CLUB_MAP:
        c_display_parts.append(f"{code} ({CLUB_MAP[code]})")
    else:
        c_display_parts.append(code)

c_display = ", ".join(c_display_parts)

print(f"Original Club Code: '{c_code_raw}'")
print(f"Displayed Club: '{c_display}'")

expected = "DN (D.N.A.), CW (Crowwood)"
if c_display == expected:
    print("PASS: Display is correct")
else:
    print(f"FAIL: Expected '{expected}', got '{c_display}'")
