import board
import busio
from adafruit_ssd1306 import SSD1306_I2C
from PIL import Image, ImageDraw, ImageFont

# Setup I2C
i2c = busio.I2C(board.SCL, board.SDA)

# Initialize display
display = SSD1306_I2C(128, 64, i2c)

# Clear display
display.fill(0)
display.show()

# Create blank image for drawing
image = Image.new("1", (display.width, display.height))
draw = ImageDraw.Draw(image)

# Draw text
font = ImageFont.load_default()
draw.text((0, 0), "Hello Max!", font=font, fill=255)

# Display image
display.image(image)
display.show()
