from chess_grading import parse_results

# Mock HTML content
mock_html_adult = """
<tr>
    <td data-column="pnum">12345</td>
    <td data-column="name">Doe, John</td>
    <td class="screen_large">Club A</td>
    <td data-column="status">A</td>
    <td data-column="standard_published">1500</td>
    <td data-column="standard_live">1510</td>
</tr>
"""

mock_html_junior = """
<tr>
    <td data-column="pnum">67890</td>
    <td data-column="name">Smith, Jane</td>
    <td class="screen_large">Club B</td>
    <td data-column="status">J14</td>
    <td data-column="standard_published">1200</td>
    <td data-column="standard_live">1250</td>
</tr>
"""


mock_html_new = """
<tr>
    <td data-column="pnum">11111</td>
    <td data-column="name">Player, New</td>
    <td class="screen_large">Club C</td>
    <td data-column="status">NEW</td>
    <td data-column="standard_published"></td>
    <td data-column="standard_live">1000</td>
</tr>
"""

mock_html_junior_unknown = """
<tr>
    <td data-column="pnum">22222</td>
    <td data-column="name">Player, Junior</td>
    <td class="screen_large">Club D</td>
    <td data-column="status">J?</td>
    <td data-column="standard_published"></td>
    <td data-column="standard_live">500</td>
</tr>
"""

def test_parse():
    print("Testing Adult Parsing...")
    res_adult = parse_results(mock_html_adult)
    player = res_adult[0]
    print(f"Age: {player['age']} (Expected 'Adult')")
    assert player['age'] == "Adult"
    
    print("\nTesting Junior Parsing...")
    res_junior = parse_results(mock_html_junior)
    player2 = res_junior[0]
    print(f"Age: {player2['age']} (Expected '14')")
    assert player2['age'] == "14"

    print("\nTesting NEW Parsing...")
    res_new = parse_results(mock_html_new)
    player3 = res_new[0]
    print(f"Age: {player3['age']} (Expected 'New')")
    assert player3['age'] == "New"
    
    print("\nTesting J? Parsing...")
    res_jun_u = parse_results(mock_html_junior_unknown)
    player4 = res_jun_u[0]
    print(f"Age: {player4['age']} (Expected 'Junior')")
    assert player4['age'] == "Junior"
    
    print("\nTests Passed!")

if __name__ == "__main__":
    test_parse()
