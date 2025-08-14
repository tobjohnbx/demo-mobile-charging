
from PIL import Image, ImageDraw, ImageFont
import board
import busio
from adafruit_ssd1306 import SSD1306_I2C

# Initialize I2C and display
i2c = busio.I2C(board.SCL, board.SDA)
display = SSD1306_I2C(128, 64, i2c)

# Clear display
display.fill(0)
display.show()

# Create image and drawing context
image = Image.new("1", (display.width, display.height))
draw = ImageDraw.Draw(image)

# Load font (you can adjust size if needed)
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)

# Draw two lines of text
draw.text((0, 0), "Line 1: Hello", font=font, fill=255)
draw.text((0, 24), "Line 2: Marcel", font=font, fill=255)

# Display image
display.image(image)
display.show()
