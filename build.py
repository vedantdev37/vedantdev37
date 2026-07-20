import requests
import os

# --- YOUR DETAILS ---
github_username = "vedantdev37" 

print(f"Fetching GitHub data for {github_username}...")

# Fetch GitHub Stats
response = requests.get(f"https://api.github.com/users/{github_username}")
user_data = response.json()

name = user_data.get("name", github_username)
bio = user_data.get("bio", "Passionate Developer & Tech Enthusiast")
repos = user_data.get("public_repos", 0)
followers = user_data.get("followers", 0)

# Read the ASCII Art you just made
try:
    with open("ascii_art.txt", "r") as f:
        ascii_art = f.read()
except FileNotFoundError:
    ascii_art = "ASCII Art not found! Run generate.py first."

# Build the README layout
readme_content = f"""
# Hi there, I'm {name} 👋

<div style="display: flex; justify-content: center;">
<pre>
{ascii_art}
</pre>
</div>

### 👨‍💻 Quick Stats
* {bio}
* 💻 **Public Repositories:** {repos}
* 👥 **Followers:** {followers}

---
🤖 *This README was auto-generated using Python!*
"""

# Save to README.md
with open("README.md", "w", encoding="utf-8") as f:
    f.write(readme_content)

print("Success! Your README.md has been generated.")