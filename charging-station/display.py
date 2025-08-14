from PIL import Image, ImageDraw, ImageFont
import board
import busio
from adafruit_ssd1306 import SSD1306_I2C
from datetime import datetime
import time

class ChargingDisplay:
    """
    Display controller for the RFID charging station
    Shows charging status, session info, and system messages
    """

    def __init__(self):
        # Initialize I2C and display
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.display = SSD1306_I2C(128, 64, self.i2c)

        # Load fonts
        try:
            self.font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
            self.font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
            self.font_tiny = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
        except OSError:
            # Fallback to default font if custom fonts not available
            self.font_large = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
            self.font_tiny = ImageFont.load_default()

        # Initialize display
        self.clear_display()
        self.show_welcome_message()

    def clear_display(self):
        """Clear the display"""
        self.display.fill(0)
        self.display.show()

    def _create_image(self):
        """Create a new image for drawing"""
        return Image.new("1", (self.display.width, self.display.height))

    def _show_image(self, image):
        """Display the image on the screen"""
        self.display.image(image)
        self.display.show()

    def show_welcome_message(self):
        """Show welcome message when system starts"""
        image = self._create_image()
        draw = ImageDraw.Draw(image)

        draw.text((10, 10), "EV Charging", font=self.font_large, fill=255)
        draw.text((15, 30), "Station Ready", font=self.font_small, fill=255)
        draw.text((5, 50), "Present RFID card", font=self.font_tiny, fill=255)

        self._show_image(image)

    def show_pricing_info(self, start_time="08:00", end_time="22:00", amount=0.1000, quantity_type="MINUTE"):
        """Show pricing information based on provided parameters

        Args:
            start_time: Start time of pricing period (e.g., "08:00")
            end_time: End time of pricing period (e.g., "22:00")
            amount: Price amount (0.0000 displays as FREE)
            quantity_type: Quantity type (e.g., "MINUTE", "SECOND", "HOUR")
        """
        image = self._create_image()
        draw = ImageDraw.Draw(image)

        # Map quantity types to shorter versions
        quantity_mapping = {
            "MINUTE": "min",
            "SECOND": "sec",
            "HOUR": "hr",
            "KILOWATT_HOUR": "kWh",
            "UNIT": "unit"
        }

        # Get short version, fallback to original if not found
        short_quantity = quantity_mapping.get(quantity_type.upper(), quantity_type.lower())

        # Determine price display text
        if amount == 0.0000:
            price_text = "FREE"
        else:
            price_text = f"€{amount:.3f}/{short_quantity}"

        time_period = f"{start_time}-{end_time}"

        # Display pricing information with more space utilization
        draw.text((15, 5), "Charging Rate", font=self.font_small, fill=255)
        draw.text((15, 25), price_text, font=self.font_large, fill=255)
        draw.text((10, 48), f"Active: {time_period}", font=self.font_small, fill=255)

        self._show_image(image)

    def show_card_detected(self, tag_id):
        """Show when RFID card is detected"""
        image = self._create_image()
        draw = ImageDraw.Draw(image)

        draw.text((20, 5), "Card Detected", font=self.font_small, fill=255)
        draw.text((10, 25), f"ID: {str(tag_id)[:10]}", font=self.font_tiny, fill=255)
        draw.text((25, 45), "Processing...", font=self.font_tiny, fill=255)

        self._show_image(image)

    def show_charging_started(self, tag_id, start_time):
        """Show charging session started"""
        image = self._create_image()
        draw = ImageDraw.Draw(image)

        draw.text((15, 0), "CHARGING", font=self.font_large, fill=255)
        draw.text((30, 20), "ACTIVE", font=self.font_large, fill=255)
        draw.text((5, 40), f"Started: {start_time.strftime('%H:%M')}", font=self.font_tiny, fill=255)
        draw.text((5, 52), f"Card: {str(tag_id)[:8]}", font=self.font_tiny, fill=255)

        self._show_image(image)

    def show_charging_active(self, start_time, duration_minutes):
        """Show ongoing charging session with duration"""
        image = self._create_image()
        draw = ImageDraw.Draw(image)

        # Blinking effect for active charging
        if int(time.time()) % 2:
            draw.text((25, 0), "CHARGING", font=self.font_small, fill=255)
        else:
            draw.text((35, 0), "⚡ ACTIVE ⚡", font=self.font_tiny, fill=255)

        draw.text((5, 20), f"Duration: {duration_minutes:.1f}min", font=self.font_tiny, fill=255)
        draw.text((5, 35), f"Started: {start_time.strftime('%H:%M')}", font=self.font_tiny, fill=255)
        draw.text((5, 50), "Present card to stop", font=self.font_tiny, fill=255)

        self._show_image(image)

    def show_charging_stopped(self, duration_minutes, cost=None):
        """Show charging session completed"""
        image = self._create_image()
        draw = ImageDraw.Draw(image)

        draw.text((10, 0), "CHARGING", font=self.font_small, fill=255)
        draw.text((20, 18), "STOPPED", font=self.font_small, fill=255)
        draw.text((5, 35), f"Duration: {duration_minutes:.1f}min", font=self.font_tiny, fill=255)

        if cost:
            draw.text((5, 47), f"Cost: €{cost:.2f}", font=self.font_tiny, fill=255)
        else:
            draw.text((5, 47), "Processing billing...", font=self.font_tiny, fill=255)

        self._show_image(image)

    def show_api_success(self, message="Billing sent"):
        """Show API operation success"""
        image = self._create_image()
        draw = ImageDraw.Draw(image)

        draw.text((35, 10), "✓ SUCCESS", font=self.font_small, fill=255)
        draw.text((10, 30), message, font=self.font_tiny, fill=255)
        draw.text((15, 50), "Ready for next", font=self.font_tiny, fill=255)

        self._show_image(image)

    def show_api_error(self, error_message="API Error"):
        """Show API operation error"""
        image = self._create_image()
        draw = ImageDraw.Draw(image)

        draw.text((30, 5), "⚠ ERROR", font=self.font_small, fill=255)
        draw.text((5, 25), error_message[:18], font=self.font_tiny, fill=255)
        draw.text((5, 40), "Session saved", font=self.font_tiny, fill=255)
        draw.text((5, 52), "locally", font=self.font_tiny, fill=255)

        self._show_image(image)

    def show_system_status(self, status_text):
        """Show general system status"""
        image = self._create_image()
        draw = ImageDraw.Draw(image)

        draw.text((20, 20), "SYSTEM", font=self.font_small, fill=255)
        draw.text((5, 40), status_text, font=self.font_tiny, fill=255)

        self._show_image(image)

    def show_temporary_message(self, message, duration=3):
        """Show a temporary message and return to previous state"""
        image = self._create_image()
        draw = ImageDraw.Draw(image)

        # Center the message
        draw.text((10, 25), message, font=self.font_small, fill=255)

        self._show_image(image)
        time.sleep(duration)
