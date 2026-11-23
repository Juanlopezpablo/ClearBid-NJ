"""Ejecutar después de migrar: python -m app.scripts.index_search_documents."""
import asyncio
from sqlalchemy import select
from app.database import get_session_maker
from app.models import Document
from app.services.document_search import index_document

async def main():
    async with get_session_maker()() as db:
        ids = (await db.scalars(select(Document.id).where(Document.search_status.in_(["pending", "error", "unavailable"])))).all()
        for document_id in ids:
            document = await db.get(Document, document_id)
            if document:
                await index_document(document)
                await db.commit()
                print(document_id, document.search_status)

if __name__ == "__main__":
    asyncio.run(main())
