from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="risenlab/agentlogs",
    repo_type="dataset",
    local_dir="/downloads/yzy/agentlogs",
    max_workers=8,
)
print("DOWNLOAD_COMPLETE")
