import os

from PIL import Image

try:
    from rembg import remove
    HAS_REMBG = True
except Exception:  # rembg is heavy; degrade gracefully if it isn't available
    HAS_REMBG = False

# Make sure your image is named profile.jpg, or change the name on the line below!
input_path = 'profile.jpg'
output_path = 'ascii_art.txt'

# Compact width so the art fits neatly into the left column of the README.
# (Was 80 — far too wide for a two-column layout.)
NEW_WIDTH = 40
# Terminal characters are taller than they are wide; this factor keeps the
# proportions from stretching vertically.
CHAR_ASPECT_CORRECTION = 0.5

source_path = input_path
if HAS_REMBG:
    try:
        print("Removing background... this might take a few seconds!")
        with open(input_path, 'rb') as i:
            output_data = remove(i.read())
        with open('temp.png', 'wb') as o:
            o.write(output_data)
        source_path = 'temp.png'
    except Exception as exc:  # e.g. model download blocked — degrade gracefully
        print(f"Background removal failed ({exc}); using the raw image instead.")
else:
    print("rembg not installed — using the raw image without background removal.")

# Convert to grayscale and resize for ASCII proportions
img = Image.open(source_path).convert('L')
width, height = img.size
aspect_ratio = height / width
new_height = int(aspect_ratio * NEW_WIDTH * CHAR_ASPECT_CORRECTION)
img = img.resize((NEW_WIDTH, new_height))

# Map the image pixels to ASCII characters (dark -> light)
chars = ["@", "#", "S", "%", "?", "*", "+", ";", ":", ",", ".", " "]
pixels = img.getdata()
# 256 / len(chars) == 21.33, so // 22 keeps every pixel inside the list bounds.
new_pixels = ''.join(chars[pixel // 22] for pixel in pixels)

# Format the flat string into rows of NEW_WIDTH characters
ascii_image = "\n".join(
    new_pixels[index:index + NEW_WIDTH]
    for index in range(0, len(new_pixels), NEW_WIDTH)
)

with open(output_path, "w") as f:
    f.write(ascii_image)

# Inject the art into README.md between the ASCII markers so the profile
# page updates automatically (keeps README as the single rendered source).
readme_path = 'README.md'
start_marker = '<!-- ASCII:START -->'
end_marker = '<!-- ASCII:END -->'
if os.path.exists(readme_path):
    with open(readme_path, 'r', encoding='utf-8') as f:
        readme = f.read()
    if start_marker in readme and end_marker in readme:
        import re
        block = f"{start_marker}\n{ascii_image}\n{end_marker}"
        readme = re.sub(
            re.escape(start_marker) + r".*?" + re.escape(end_marker),
            block,
            readme,
            flags=re.DOTALL,
        )
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme)
        print("Injected ASCII art into README.md")

# Clean up the temporary file
if os.path.exists("temp.png"):
    os.remove("temp.png")

print(f"Success! Wrote {output_path} ({NEW_WIDTH} cols x {new_height} rows).")
