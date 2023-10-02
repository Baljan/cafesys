from cafesys.baljan.tasks import update_stats

# Call the Celery task
result = update_stats.delay()