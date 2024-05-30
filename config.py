from selenium.webdriver.chrome.options import Options

import chromedriver_autoinstaller

# import geckodriver_autoinstaller
from pyvirtualdisplay import Display
from pydantic_settings import BaseSettings


# geckodriver_autoinstaller.install()
chromedriver_autoinstaller.install()


display = Display(visible=False, size=(800, 900))
display.start()


selenium_options = Options()
selenium_options.add_argument("start-maximized")
selenium_options.add_argument("disable-infobars")
selenium_options.add_argument("--disable-extensions")
selenium_options.add_argument("--disable-gpu")
selenium_options.add_argument("--disable-dev-shm-usage")
selenium_options.add_argument("--no-sandbox")


class Settings(BaseSettings):
    token: str = ''
    chat_ids: str = ''
    async_delay: int = 10
    db_user: str = "tbot"
    db_pass: str = "tbot"
    db_name: str = "tbot"
    db_host: str = "db"
    db_port: str = "5432"
    debug: bool = False

    class Config:
        env_prefix = "TBOT_"


settings = Settings()
