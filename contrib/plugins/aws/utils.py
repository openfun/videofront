VIDEO_FOLDER_KEY_PATTERN = "videos/{video_id}"
VIDEO_KEY_PATTERN = VIDEO_FOLDER_KEY_PATTERN + "/{resolution}/video.mp4"

def get_video_folder_key(video_id):
    """
    Get the S3 folder key associated to this video.
    """
    return VIDEO_FOLDER_KEY_PATTERN.format(video_id=video_id)

def get_video_key(video_id, resolution):
    """
    Get the S3 object key associated to this video with the given resolution.
    """
    return VIDEO_KEY_PATTERN.format(video_id=video_id, resolution=resolution)
