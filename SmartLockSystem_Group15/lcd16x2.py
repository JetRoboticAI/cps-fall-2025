# lcd16x2.py
from RPLCD.i2c import CharLCD

I2C_ADDR = 0x27
lcd = CharLCD(i2c_expander='PCF8574', address=I2C_ADDR,
              cols=16, rows=2, charmap='A00', auto_linebreaks=True)

def lcd_print(line1: str, line2: str = ""):
    """Show up to 16 chars per line on the LCD, and also print to shell."""
    print(line1)
    if line2:
        print(line2)
    lcd.clear()
    # Trim/pad to fit 16 chars
    l1 = (line1 or "")[:16]
    l2 = (line2 or "")[:16]
    lcd.write_string(l1)
    if l2:
        lcd.crlf()
        lcd.write_string(l2)

def lcd_clear():
    lcd.clear()

if __name__ == "__main__":
    lcd_print("Hello, world!", "I2C LCD ready")
