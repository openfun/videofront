import os

from django.views import static

from .backend import Backend


def storage_video(request, video_id, format_name):
    # Serve a file directly from the filesystem
    path = Backend.get_file_path(video_id, "{}.mp4".format(format_name))
    document_root = os.path.dirname(path)
    filename = os.path.basename(path)
    return static.serve(request, filename, document_root=document_root)
