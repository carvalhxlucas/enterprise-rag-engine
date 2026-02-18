from celery import shared_task


@shared_task(name="ingest_document_task")
def ingest_document_task(file_id: str) -> None:
    return None

