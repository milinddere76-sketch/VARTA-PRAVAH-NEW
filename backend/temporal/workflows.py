from datetime import timedelta
from temporalio import workflow
from .activities import (
    fetch_news_activity,
    generate_script_activity,
    synclabs_lip_sync_activity,
    check_sync_labs_status_activity,
    upload_to_s3_activity,
    start_stream_activity
)

@workflow.defn
class NewsProductionWorkflow:
    @workflow.run
    async def run(self, input_data: dict) -> str:
        channel_id = input_data["channel_id"]
        language = input_data["language"]
        stream_key = input_data["stream_key"]
        # 1. Fetch News
        news_data = await workflow.execute_activity(
            fetch_news_activity,
            language,
            start_to_close_timeout=timedelta(seconds=60)
        )
        
        script_data = await workflow.execute_activity(
            generate_script_activity,
            {"news_data": news_data, "language": language},
            start_to_close_timeout=timedelta(seconds=120)
        )
        
        # 3. Request Lip-Sync from Sync Labs
        job_id = await workflow.execute_activity(
            synclabs_lip_sync_activity,
            script_data,
            start_to_close_timeout=timedelta(seconds=60)
        )
        
        # 4. Wait for Lip-Sync to complete
        status = "pending"
        final_video_url = ""
        
        while status != "completed":
            await workflow.sleep(timedelta(seconds=30))
            result = await workflow.execute_activity(
                check_sync_labs_status_activity,
                job_id,
                start_to_close_timeout=timedelta(seconds=60)
            )
            status = result["status"]
            final_video_url = result["video_url"]
            
        # 5. Upload to S3
        s3_url = await workflow.execute_activity(
            upload_to_s3_activity,
            final_video_url,
            start_to_close_timeout=timedelta(seconds=300)
        )
        
        # 6. Start / Update Stream
        await workflow.execute_activity(
            start_stream_activity,
            {
                "channel_id": channel_id,
                "stream_key": stream_key,
                "video_url": s3_url
            },
            start_to_close_timeout=timedelta(seconds=60)
        )
        
        return s3_url
