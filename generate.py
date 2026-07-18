from PIL import Image
from rembg import remove
import os

# Make sure your image is named profile.jpg, or change the name on the line below!
input_path = 'profile.jpg' 
output_path = 'ascii_art.txt'

print("Removing background... this might take a few seconds!")

# Read the image and remove the background
with open(input_path, 'rb') as i:
    input_data = i.read()
    output_data = remove(input_data)
    
with open('temp.png', 'wb') as o:
    o.write(output_data)

# Convert to grayscale and resize for ASCII proportions
img = Image.open('temp.png').convert('L')
width, height = img.size
aspect_ratio = height / width
new_width = 80
new_height = int(aspect_ratio * new_width * 0.5) 
img = img.resize((new_width, new_height))

# Map the image pixels to ASCII characters
chars = ["@", "#", "S", "%", "?", "*", "+", ";", ":", ",", ".", " "]
pixels = img.getdata()
new_pixels = [chars[pixel // 22] for pixel in pixels]
new_pixels = ''.join(new_pixels)

# Format the text into an image block
ascii_image = [new_pixels[index:index + new_width] for index in range(0, len(new_pixels), new_width)]
ascii_image = "\n".join(ascii_image)

# Save to a text file
with open(output_path, "w") as f:
    f.write(ascii_image)

# Clean up the temporary file
if os.path.exists("temp.png"):
    os.remove("temp.png")

print("Success! Check your folder for ascii_art.txt")