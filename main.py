import subprocess
from html import escape
from uuid import uuid4

from time import sleep
import asyncio
from typing import Optional
from datetime import datetime
from db import DB

from telegram.constants import ParseMode
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    MessageHandler,
    Application,
    filters,
    CallbackQueryHandler,
    InlineQueryHandler,
)

from parser import parsers, BaseParser
from model import logger
from config import settings
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
)


class Tbot:
    db = DB()
    chat_ids = [int(i) for i in settings.chat_ids.split()]
    token = settings.token
    parsers: [BaseParser] = parsers
    prev_error_message: Optional[int] = None

    ############################### Bot ############################################
    async def start(self, update, context):
        await update.message.reply_text(
            await self.main_menu_message(), reply_markup=await self.main_menu_keyboard()
        )

    async def main_menu(self, update, context):
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            text=await self.main_menu_message(),
            reply_markup=await self.main_menu_keyboard(),
        )

    async def first_menu(self, update, context):
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            text=await self.first_menu_message(),
            reply_markup=await self.first_menu_keyboard(),
        )

    async def second_menu(self, update, context):
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            text=await self.second_menu_message(),
            reply_markup=await self.second_menu_keyboard(),
        )

    async def third_menu(self, update, context):
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            text=await self.third_menu_message(),
            reply_markup=await self.third_menu_keyboard(),
        )

        # and so on for every callback_data option

    async def first_submenu(self, bot, update):
        pass

    async def second_submenu(self, bot, update):
        pass

    ############################ Keyboards #########################################

    async def main_menu_keyboard(self):
        # keyboard = [[InlineKeyboardButton('Option 1', callback_data='m1')],
        #             [InlineKeyboardButton('Option 2', callback_data='m2')],
        #             [InlineKeyboardButton('Option 3', callback_data='m3')]]
        books = [" ".join(i.title) for i in await self.db.get_books()]
        keyboard = [
            [InlineKeyboardButton(i, callback_data=f"m{ind}")]
            for ind, i in enumerate(sorted(books))
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    async def first_menu_keyboard():
        keyboard = [
            [InlineKeyboardButton("Submenu 1-1", callback_data="m1_1")],
            [InlineKeyboardButton("Submenu 1-2", callback_data="m1_2")],
            [InlineKeyboardButton("Main menu", callback_data="main")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    async def second_menu_keyboard():
        keyboard = [
            [InlineKeyboardButton("Submenu 2-1", callback_data="m2_1")],
            [InlineKeyboardButton("Submenu 2-2", callback_data="m2_2")],
            [InlineKeyboardButton("Main menu", callback_data="main")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    async def third_menu_keyboard():
        keyboard = [
            [InlineKeyboardButton("Submenu 3-1", callback_data="m2_1")],
            [InlineKeyboardButton("Submenu 3-2", callback_data="m2_2")],
            [InlineKeyboardButton("Main menu", callback_data="main")],
        ]
        return InlineKeyboardMarkup(keyboard)

    ############################# Messages #########################################
    @staticmethod
    async def main_menu_message():
        return "Choose the option in main menu:"

    @staticmethod
    async def first_menu_message():
        return "Choose the submenu in first menu:"

    @staticmethod
    async def second_menu_message():
        return "Choose the submenu in second menu:"

    @staticmethod
    async def third_menu_message():
        return "Choose the submenu in second menu:"

    async def send_welcome(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(f"Hello {update.effective_user.first_name}")

    async def books_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        messages = []
        books = await self.db.get_books(1)
        for i in books:
            book = str(i)
            message = f"\n {i.title}   Видалити: /del_{i.id}"
            if len(messages) and (len(messages[-1]) + 1 + len(message)) < 4000:
                messages[-1] += message
            else:
                messages.append(message)
        for message in messages:
            await context.bot.send_message(update.effective_chat.id, message)

    async def echo_all(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        books = self.db.prepare_books(update.message.text, 1)
        books_to_write_str_list = await self.db.add_books(books)
        if not books_to_write_str_list:
            message = "книги вже є в списку"
        else:
            message = "\n".join(
                [i + " додана" for i in books_to_write_str_list]
            )
        # with open('some.txt', 'w') as f:
        #     f.write('\n'.join([str(i) for i in await self.books_to_find.get_books()]))
        await update.message.reply_text(message)

    async def report_book(self, parser, context: ContextTypes.DEFAULT_TYPE):
        books = await parser.run()
        for chat in self.chat_ids:
            for book in books:
                try:
                    await context.bot.send_photo(
                        chat, book.image, f"{book.price} | {book.title}\n{book.link}\n В пошуку: {book.parent.title} \n Видалити з пошуку: /del_{book.parent.id}"
                    )
                except Exception as e:
                    logger.error(f"Cant send image\n         {e}")
                    await context.bot.send_message(
                        chat, f"{book.price} | {book.title}\n{book.link}"
                    )
                await asyncio.sleep(0.1)
        # await asyncio.sleep(settings.async_delay)

    async def check_works(self, context):

        not_works = [parser.name for parser in self.parsers if not parser.works]
        if self.prev_error_message:
            await context.bot.delete_message(self.chat_ids[0], self.prev_error_message)
        if not_works:
            x = await context.bot.send_message(
                self.chat_ids[0], f'Not works {", ".join(not_works)}'
            )
            self.prev_error_message = x.id
            logger.error(f'Not works {", ".join(not_works)}')
        else:
            x = await context.bot.send_message(self.chat_ids[0], f"OK")
            self.prev_error_message = x.id

    async def delete_book(self, update, context):
        """Sends a message with three inline buttons attached."""
        message = update.message.text
        print(message)
        book_id_str:str = message.split("/del_")[1]
        if not book_id_str.isdigit():
            await update.message.reply_text('Не існує')
            return
        book = await self.db.get_book(int(book_id_str))
        if not book:
            await update.message.reply_text('Не існує')
            return
        keyboard = [
            [
                InlineKeyboardButton("Yes", callback_data=book.id),
                InlineKeyboardButton("No", callback_data="0"),
            ],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(f'Дійсно видалити "{book.title}" з пошуку?', reply_markup=reply_markup)

    async def button(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Parses the CallbackQuery and updates the message text."""
        query = update.callback_query

        # CallbackQueries need to be answered, even if no notification to the user is needed
        # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
        a = await query.answer()
        if a:
            reesult = await self.db.delete_book(int(query.data))
            print(reesult)
            await query.edit_message_text(text=f"Видалено")

    async def parse(self, context: ContextTypes.DEFAULT_TYPE):
        logger.debug("Parse started")
        self.prev_error_message = None
        while True:
            t1 = datetime.now()
            # corutines = [self.report_book(i, context) for i in self.parsers]
            if settings.debug:
                for i in self.parsers:
                    await self.report_book(i, context)
            else:

                try:
                    # await asyncio.gather(*corutines)

                    for i in self.parsers:
                        await self.report_book(i, context)
                except Exception as e:
                    logger.error(f"gather down: {e}")
            if settings.debug:
                await self.check_works(context)
            else:
                try:
                    await self.check_works(context)
                # await asyncio.sleep(5)
                except Exception as e:
                    logger.error(f"Parser down: {e}")
            # print(datetime.now() - t1)

    def clean_sync(self):
        subprocess.run("rm -r /tmp/.com.google.Chrome.*", shell=True)
        subprocess.run("rm -r /tmp/.org.chromium.Chromium.*", shell=True)

    async def clean_data(self, *args, **kwargs):
        logger.info("clean")
        await asyncio.to_thread(self.clean_sync)

    async def books_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.inline_query.query

        if not query:  # empty query should not be handled
            return
        print(query)
        results = [
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="Caps",
                input_message_content=InputTextMessageContent(query.upper()),
            ),
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="Book",
                input_message_content=InputTextMessageContent(
                    f"<i>{escape(query)}</i>", parse_mode=ParseMode.HTML
                ),
            ),
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="Bold",
                input_message_content=InputTextMessageContent(
                    f"<b>{escape(query)}</b>", parse_mode=ParseMode.HTML
                ),
            ),
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="Italic",
                input_message_content=InputTextMessageContent(
                    f"<i>{escape(query)}</i>", parse_mode=ParseMode.HTML
                ),
            ),
        ]

        await update.inline_query.answer(results)

    def run(self):
        application = Application.builder().token(self.token).build()

        application.add_handler(CommandHandler("all", self.books_list))
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(MessageHandler(filters.Regex('/del_'),  self.delete_book))
        application.add_handler(CallbackQueryHandler(self.button))

        application.add_handler(CallbackQueryHandler(self.main_menu, pattern="main"))
        application.add_handler(CallbackQueryHandler(self.first_menu, pattern="m1"))
        application.add_handler(CallbackQueryHandler(self.second_menu, pattern="m2"))
        application.add_handler(CallbackQueryHandler(self.third_menu, pattern="m3"))
        application.add_handler(InlineQueryHandler(self.books_query))

        application.add_handler(
            CallbackQueryHandler(self.first_submenu, pattern="m1_1")
        )
        application.add_handler(
            CallbackQueryHandler(self.second_submenu, pattern="m2_1")
        )
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.echo_all)
        )
        j = application.job_queue
        j.run_repeating(self.clean_data, interval=60 * 60, first=1)
        j.run_once(self.parse, 1)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            application.run_polling(allowed_updates=Update.ALL_TYPES)
        except Exception as e:
            logger.error(f"Polling down: {e}")

            asyncio.run(application.stop())
            sleep(2)
            asyncio.run(application.start())


if __name__ == "__main__":
    tbot = Tbot()
    tbot.run()
