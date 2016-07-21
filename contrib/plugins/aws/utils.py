VIDEO_KEY_PATTERN = "videos/src/{video_id}/video.mp4"

def get_video_key(video_id):
    return VIDEO_KEY_PATTERN.format(video_id=video_id)
