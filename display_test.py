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

# Load a simple sans-serif font in larger size
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)

# Draw text
draw.text((0, 20), "Hello Max!", font=font, fill=255)

# Display image
display.image(image)
display.show()
