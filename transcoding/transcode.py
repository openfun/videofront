import logging
import subprocess

from pipeline.models import Playlist, VideoFormat
from transcoding.tasks_extra import apply_new_transcoding


TRANSCODE_COST_PER_MIN_VIDEO = 0.017
TRANSCODE_COST_PER_MIN_AUDIO = 0.00522


logger = logging.getLogger('video-transcoding')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
fh = logging.FileHandler('/var/tmp/video-transcode.log')
fh.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)


def get_videos_to_be_transcoded(course_key):
    logger.info("Trying to retreive playlist for course key '{}'".format(course_key))
    playlist = Playlist.objects.get(name=course_key)
    logger.info("Processing course '{}'".format(course_key))
    to_be_transcoded = playlist.videos.exclude(
        formats__name='UL',
    ).exclude(processing_state__status='failed')
    return to_be_transcoded.all()


def estimate_cost(course_key):
    duration_list = []
    for video in get_videos_to_be_transcoded(course_key):
        try:
            sd_url = video.formats.get(name='LD').url
        except VideoFormat.DoesNotExist:
            logger.warning("    Could not find URL for video '{}'".format(video))
            video_duration = 0
            sd_url = None
        if sd_url:
            cmd = 'ffprobe -i {url} -show_entries format=duration -v quiet -of csv="p=0"'.format(url=sd_url)
            cmd_out = subprocess.check_output(cmd, shell=True)
            video_duration = float(cmd_out)
            logger.info("    Duration for video {} is : {}".format(video, video_duration))
        duration_list.append(video_duration)
    duration_sec = sum(duration_list)
    duration = duration_sec / 60
    cost_video = duration * TRANSCODE_COST_PER_MIN_VIDEO
    cost_audio = duration * TRANSCODE_COST_PER_MIN_AUDIO
    total_cost = cost_video + cost_audio
    logger.info("Found videos durations: {}".format(duration_list))
    logger.info("Total duration: {} s = {} min".format(duration_sec, duration))
    logger.info("Transcode video cost for course '{}': {} USD".format(course_key, cost_video))
    logger.info("Transcode audio cost for course '{}': {} USD".format(course_key, cost_audio))
    logger.info("#### Total transcode cost for course '{}': {} USD".format(course_key, total_cost))
    return total_cost


def transcode_video(course_key):
    for video in get_videos_to_be_transcoded(course_key):
        logger.info("    Applying new transcoding to video '{}'".format(video.public_id))
        apply_new_transcoding(video.public_id)


def transcode_for_courses(course_key_list):
    '''
    Run video transcode for a list of courses.
    Takes a list of course keys separated by spaces.
    '''
    course_keys = course_key_list.split()
    cost_for_all_courses = []
    for course_key in course_keys:
        cost = estimate_cost(course_key)
        cost_for_all_courses.append(cost)
    total_cost = sum(cost_for_all_courses)
    logger.info("#### Cost for all the courses {} USD".format(total_cost))
    response = input("Type 'Yes/Y' to continue:  ")
    if response.lower() not in ['yes', 'y']:
        return
    for course_key in course_keys:
        transcode_video(course_key)
