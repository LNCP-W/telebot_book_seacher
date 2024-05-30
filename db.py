import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import text
from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    update,
    Insert,
)
from sqlalchemy.future import select
from sqlalchemy.pool import NullPool

from model import BookToFind, User, BookInput, ProcessedBooks
from config import settings


postgres_url = f"postgresql+asyncpg://{settings.db_user}:{settings.db_pass}@{settings.db_host}:{settings.db_port}/{settings.db_name}"
engine = create_async_engine(
    postgres_url, future=True, echo=settings.debug, poolclass=NullPool
)
async_session = async_sessionmaker(engine, expire_on_commit=False)

Base = declarative_base()

clean_func = """create or replace function clean_processed()
RETURNS TRIGGER AS
$function$
	declare
	    i integer;
	   cou integer;
	BEGIN
		for i in select site_id from processed p group by site_id
		LOOP
			cou := (select count(*) from processed where site_id = i);
			if cou > 2000 THEN
				delete from processed where id < (select id from processed where site_id = i order by id offset cou -1500 limit 1 );
			end if;
		end loop;
	RETURN NEW;
	end;
$function$
language plpgsql;


CREATE TRIGGER tr_clean_processed
after INSERT ON processed
FOR EACH STATEMENT EXECUTE PROCEDURE clean_processed();
"""


def async_session_context(function, *args, **kwargs):
    async def inner(*args, **kwargs):
        async with async_session() as session:
            async with session.begin():
                try:
                    x = await function(*args, **kwargs, db_session=session)
                    await session.commit()
                    return x

                except:
                    await session.rollback()
                    raise
                finally:
                    await session.close()

    return inner


class DBUsers(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, unique=True)
    name = Column(String(100))


class DBBooks(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True)
    user_id = Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(150), nullable=False)
    exclude = Column(String(150), nullable=True)


class DBSite(Base):
    __tablename__ = "site"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)


class DBProcessed(Base):
    __tablename__ = "processed"
    id = Column(Integer, primary_key=True)
    book_id = Column(String(100), nullable=False)
    site_id = Column(ForeignKey("site.id", ondelete="CASCADE"), nullable=False)
    parent_book = Column(ForeignKey("books.id", ondelete="CASCADE"), nullable=True)
    link = Column(String(200), nullable=True)


class DB:
    __POSSIBLE_FUNCTIONS = {
     'add_books',
     'add_processed',
     'add_user',
     'change_book',
     'create_clean_func',
     'delete_book',
     'delete_site',
     'delete_user',
     'get_books',
     'get_or_add_site',
     'get_processed',
     'get_user'
    }

    @async_session_context
    async def add_user(self, user: User, db_session: async_session) -> int | bool:
        req = await db_session.execute(
            select(DBUsers).where(DBUsers.chat_id == user.chat_id)
        )
        exists_user = req.scalars().one_or_none()
        if exists_user:
            return False
        new_user = DBUsers(**user.model_dump())
        db_session.add(new_user)
        await db_session.flush()
        return new_user.id

    @async_session_context
    async def delete_user(
        self,
        user_id: int = None,
        chat_id: int = None,
        db_session: async_session = async_session(),
    ) -> bool:
        if not user_id and not chat_id:
            raise ValueError
        user = await db_session.execute(
            select(DBUsers).where(
                DBUsers.id == user_id if user_id else DBUsers.chat_id == chat_id
            )
        )
        user = user.scalars().one_or_none()
        if not user:
            return False
        await db_session.delete(user)
        return True

    @async_session_context
    async def get_or_add_site(self, site_name: str, db_session: async_session) -> int:
        req = await db_session.execute(select(DBSite).where(DBSite.name == site_name))
        site_exists = req.scalars().one_or_none()
        if site_exists:
            return site_exists.id
        new_site = DBSite(name=site_name)
        db_session.add(new_site)
        await db_session.flush()
        return new_site.id

    @async_session_context
    async def delete_site(self, site_id: int, db_session: async_session) -> bool:
        site = await db_session.execute(select(DBSite).where(DBSite.id == site_id))
        site_to_delete = site.scalars().one_or_none()
        if not site_to_delete:
            return False
        await db_session.delete(site_to_delete)
        return True

    @async_session_context
    async def get_user(
        self,
        user_id: int = None,
        chat_id: int = None,
        db_session: async_session = async_session(),
    ) -> User | None:
        if not user_id and not chat_id:
            raise ValueError
        req = await db_session.execute(
            select(DBUsers).where(
                DBUsers.id == user_id if user_id else DBUsers.chat_id == chat_id
            )
        )
        user = req.scalars().one_or_none()
        return user

    @async_session_context
    async def add_books(self, books: [BookToFind], db_session: async_session) -> [str]:
        req = await db_session.execute(
            select(DBBooks.title).where(DBBooks.user_id == books[0].user_id)
        )
        existed_books = req.scalars().all()
        books_to_add = [
            book.model_dump() for book in books if book.title not in existed_books
        ]
        if not books_to_add:
            return []
        await db_session.execute(Insert(DBBooks), books_to_add)
        await db_session.flush()
        return [i['title'] for i in books_to_add]
    def prepare_books(self, books_mesage: str, user_id:int) -> [BookToFind]:
        books = [i.strip() for i in books_mesage.lower().strip().split("\n")]
        books_to_write = []
        for book in books:
            li = book.split(", ")
            if len(li):
                book = BookToFind(title=li[0], user_id=user_id)
                if len(li) > 1:
                    book.exclude = li[1]
                books_to_write.append(book)
        return books_to_write
    @async_session_context
    async def get_books(self, user_id: int, db_session: async_session) -> [BookToFind]:
        req = await db_session.execute(
            select(DBBooks).where(DBBooks.user_id == user_id)
        )
        books = req.scalars().all()
        return [BookToFind(**i.__dict__) for i in books]

    @async_session_context
    async def get_book(self, book_id: int, db_session: async_session) -> [BookToFind]:
        req = await db_session.execute(
            select(DBBooks).where(DBBooks.id == book_id)
        )
        book = req.scalars().one_or_none()
        return book


    @async_session_context
    async def delete_book(self, book_id: int, db_session: async_session) -> bool:
        book = await db_session.execute(select(DBBooks).where(DBBooks.id == book_id))
        book_to_delete = book.scalars().one_or_none()
        if not book_to_delete:
            return False
        await db_session.delete(book_to_delete)
        return True

    @async_session_context
    async def change_book(
        self, book_id: int, new_book: BookToFind, db_session: async_session
    ) -> bool:
        book = await db_session.execute(select(DBBooks).where(DBBooks.id == book_id))
        book_to_update = book.scalars().one_or_none()
        if not book_to_update:
            return False
        values = new_book.model_dump(exclude_none=True)
        await db_session.execute(
            update(DBBooks).where(DBBooks.id == book_id).values(**values)
        )
        await db_session.flush()
        return True

    @async_session_context
    async def add_processed(
        self, books: list[BookInput], site_id: int, db_session: async_session
    ) -> bool:
        processed_to_add = []
        for book in books:
            parent = book.parent.id if book.parent else None
            b = ProcessedBooks(book_id=book.book_id, site_id=site_id, link = book.link, parent_book=parent).model_dump(exclude_none=True)
            processed_to_add.append(b)
        await db_session.execute(Insert(DBProcessed), processed_to_add)
        await db_session.flush()
        return True

    @async_session_context
    async def get_processed(self, site_id: int, db_session: async_session) -> [str]:
        req = await db_session.execute(
            select(DBProcessed.book_id).where(DBProcessed.site_id == site_id)
        )
        books_ids = req.scalars().all()
        return books_ids


    @async_session_context
    @staticmethod
    async def create_clean_func(db_session: async_session):
        clean_func = """create or replace function clean_processed()
        RETURNS TRIGGER AS
        $function$
        	declare
        	    i integer;
        	   cou integer;
        	BEGIN
        		for i in select site_id from processed p group by site_id
        		LOOP
        			cou := (select count(*) from processed where site_id = i and parent_book IS NULL);
        			if cou > 2000 THEN
        				delete from processed where id < (select id from processed where site_id = i and parent_book IS NULL order by id offset cou -1500 limit 1 );
        			end if;
        		end loop;
        	RETURN NEW;
        	end;
        $function$
        language plpgsql;


        CREATE or replace TRIGGER tr_clean_processed
        after INSERT ON processed
        FOR EACH STATEMENT EXECUTE PROCEDURE clean_processed();
        """
        await db_session.execute(text(clean_func))

async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # await DB.create_clean_func()

asyncio.run(create_db())
c=1
