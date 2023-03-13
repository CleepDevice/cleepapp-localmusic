#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from cleep.exception import InvalidParameter, CommandError
from cleep.core import CleepRenderer
from cleep.common import CATEGORIES, RENDERERS
from cleep.profiles.alarmprofile import AlarmProfile


class Localmusic(CleepRenderer):
    """
    Localmusic application
    """

    MODULE_AUTHOR = "Cleep"
    MODULE_VERSION = "1.0.0"
    MODULE_LABEL = "Local music"
    MODULE_DEPS = ["audioplayer"]
    MODULE_DESCRIPTION = "Create your music playlist with device files"
    MODULE_LONGDESCRIPTION = (
        "Create your playlist with music files uploaded to your devices"
    )
    MODULE_TAGS = ["music", "playlist", "local"]
    MODULE_CATEGORY = CATEGORIES.MEDIA
    MODULE_URLINFO = "https://github.com/CleepDevice/cleepapp-localmusic"
    MODULE_URLHELP = None
    MODULE_URLSITE = None
    MODULE_URLBUGS = "https://github.com/CleepDevice/cleepapp-localmusic/issues"

    MODULE_CONFIG_FILE = "localmusic.conf"
    DEFAULT_CONFIG = {
        "default": None,
        "playlists": {},
    }

    RENDERER_PROFILES = [AlarmProfile]
    RENDERER_TYPE = RENDERERS.AUDIO

    ALLOWED_MUSIC_EXTENSIONS = ["mp3", "flac", "aac", "ogg"]  # supported by audioplayer

    def __init__(self, bootstrap, debug_enabled):
        """
        Constructor

        Args:
            bootstrap (dict): bootstrap objects
            debug_enabled: debug status
        """
        CleepRenderer.__init__(self, bootstrap, debug_enabled)

        self.has_audioplayer = False
        # music files
        # [
        #   {
        #       filename (str): filename
        #       path (str): full filepath
        #   },
        #   ...
        # ]
        self.files = []
        self.playback = {
            "playeruuid": None,
            "index": None,
            "playlistname": None,
        }

        self.playback_update_event = self._get_event("audioplayer.playback.update")

    def _configure(self):
        """
        Configure module
        """
        self._refresh_music_files()
        self._check_playlists()

    def _on_start(self):
        """
        Start module
        """
        self.has_audioplayer = self.is_module_loaded("audioplayer")

    def on_event(self, event):
        """
        Event received

        Args:
            event (MessageRequest): event data
        """
        if event["event"] == "audioplayer.playback.update":
            if event["params"]["playeruuid"] != self.playback["playeruuid"]:
                return

            if event["params"]["state"] == "stopped":
                # player stopped, delete its reference
                self.playback["playeruuid"] = None

            if event["params"]["state"] == "playing":
                # store current index
                self.playback["index"] = event["params"]["index"]

    def on_render(self, profile_name, profile_values):
        """
        Render event received

        Args:
            profile_name (str): rendered profile name
            profile_values (dict): renderer profile values
        """
        if (
            profile_name == "AlarmProfile"
            and profile_values["status"] == AlarmProfile.STATUS_TRIGGERED
        ):
            self._start_alarm(
                profile_values["volume"],
                profile_values["repeat"],
                profile_values["shuffle"],
            )

        if profile_name == "AlarmProfile" and profile_values["status"] in [
            AlarmProfile.STATUS_STOPPED,
            AlarmProfile.STATUS_SNOOZED,
        ]:
            snoozed = profile_values["status"] == AlarmProfile.STATUS_SNOOZED
            self._stop_alarm(snoozed)

    def _refresh_music_files(self):
        """
        Load all music files from filesystem
        """
        musics = []

        for root, _, files in os.walk(self.APP_STORAGE_PATH):
            for filename in files:
                musics.append(
                    {"filename": filename, "path": os.path.join(root, filename)}
                )

        self.files = musics

    def _check_playlists(self, playlists=None):
        """
        Keep in sync saved playlist tracks with local files

        Args:
            playlists (dict): if specified check its content. If not specified load playlists from config
        """
        playlists = self._get_config_field("playlists") if not playlists else playlists
        for playlist_name, playlist_tracks in playlists.copy().items():
            for playlist_track in playlist_tracks[:]:
                found = next(
                    (
                        track
                        for track in self.files
                        if track["filename"] == playlist_track
                    ),
                    None,
                )
                if not found:
                    self.logger.warning(
                        'Playlist "%s" has track "%s" that does not exists. Track deleted.',
                        playlist_name,
                        playlist_track,
                    )
                    playlist_tracks.remove(playlist_track)
            if len(playlist_tracks) == 0:
                self.logger.warning(
                    'Playlist "%s" is deleted because there is no track inside',
                    playlist_name,
                )
                del playlists[playlist_name]

        self._set_config_field("playlists", playlists)

    def get_music_files(self):
        """
        Get all music files stored in device

        Returns:
            list: list of files::

                [
                    {
                        filename (str): filename,
                        path (str): path
                    },
                    ...
                ]

        """
        return self.files

    def get_playback(self):
        """
        Return playback

        Returns:
            dict: current playback information::

                {
                    playeruuid (str): player uuid if running. None if not running
                    playlistname (str): current played playlist. None if no playlist played
                    index (number): current played playlist track. None if no playlist played
                }

        """
        return self.playback

    def add_music_file(self, filepath):
        """
        Add music file to device filesystem

        Args:
            filepath (str): uploaded track filepath

        Returns:
            bool: True if upload succeed

        Raises:
            InvalidParameter: if file extension is not supported
            CommandError: if adding file failed
        """
        file_ext = os.path.splitext(filepath)
        if file_ext[1][1:] not in Localmusic.ALLOWED_MUSIC_EXTENSIONS:
            raise InvalidParameter(
                f"Invalid file extension (only {','.join(Localmusic.ALLOWED_MUSIC_EXTENSIONS)} allowed)"
            )

        filename = os.path.basename(filepath)
        new_path = os.path.join(self.APP_STORAGE_PATH, filename)
        if os.path.exists(new_path):
            raise CommandError(f'Music file "{filename}" already exists')
        if not self.cleep_filesystem.move(filepath, new_path):
            raise CommandError(f'Unable to save "{filename}"')

        self._refresh_music_files()

        return True

    def delete_music_file(self, filename):
        """
        Delete music file from device filesystem

        Args:
            filename (str): filename of file to delete

        Raises:
            CommandError: if file deletion failed
        """
        for root, _, files in os.walk(self.APP_STORAGE_PATH):
            for filename_ in files:
                filepath = os.path.join(root, filename_)
                if filename_ == filename:
                    if not self.cleep_filesystem.rm(filepath):
                        raise CommandError(f'Unable to delete "{filename}"')

                    self._refresh_music_files()
                    return

        raise InvalidParameter(f'File "{filename}" was not found')

    def add_playlist(self, playlist_name, files):
        """
        Add new playlist using specified tracks

        Args:
            playlist_name (str): playlist name
            files (list): list of files to add into playlist

        Raises:
            InvalidParameter
        """
        self._check_parameters(
            [
                {"name": "playlist_name", "value": playlist_name, "type": str},
                {
                    "name": "files",
                    "value": files,
                    "type": list,
                    "validator": lambda v: len(v) > 0,
                    "message": "Playlist must not be empty",
                },
            ]
        )
        playlists = self._get_config_field("playlists")
        self.logger.debug("playlists = %s", playlists)
        if playlist_name in playlists:
            raise InvalidParameter(f'Playlist "{playlist_name}" already exists')

        playlists[playlist_name] = files
        self._check_playlists(playlists)
        self._set_config_field("playlists", playlists)

        if len(playlists) == 1:
            # set unique playlist as default one
            self.set_default_playlist(playlist_name)

    def update_playlist(self, playlist_name, new_playlist_name, files):
        """
        Update playlist content
        Set new_playlist_name to the same value as playlist_name if you don't want to rename it

        Args:
            playlist_name (str): playlist name
            new_playlist_name (str): new playlist name
            files (list): list of files to add into playlist

        Raises:
            InvalidParameter
        """
        self._check_parameters(
            [
                {"name": "playlist_name", "value": playlist_name, "type": str},
                {"name": "new_playlist_name", "value": new_playlist_name, "type": str},
                {
                    "name": "files",
                    "value": files,
                    "type": list,
                    "validator": lambda v: len(v) > 0,
                    "message": "Playlist must not be empty",
                },
            ]
        )
        playlists = self._get_config_field("playlists")
        if playlist_name not in playlists:
            raise InvalidParameter(f'Playlist "{playlist_name}" does not exist')

        new_playlist_name = (
            playlist_name if not new_playlist_name else new_playlist_name
        )

        playlists[new_playlist_name] = files
        if playlist_name != new_playlist_name:
            del playlists[playlist_name]
        self._check_playlists(playlists)
        self._set_config_field("playlists", playlists)

    def delete_playlist(self, playlist_name):
        """
        Delete playlist

        Args:
            playlist_name (str): playlist name

        Raises:
            InvalidParameter: if playlist name does not exist
        """
        playlists = self._get_config_field("playlists")
        if playlist_name not in playlists:
            raise InvalidParameter(f'Playlist "{playlist_name}" does not exist')

        del playlists[playlist_name]
        self._set_config_field("playlists", playlists)

    def set_default_playlist(self, playlist_name):
        """
        Set default playlist. This is the playlist used to be played

        Args:
            playlist_name (str): playlist name to rename

        Raises:
            InvalidParameter
        """
        playlists = self._get_config_field("playlists")
        if playlist_name not in playlists:
            raise InvalidParameter(f'Playlist "{playlist_name}" does not exist')

        self._set_config_field("default", playlist_name)

    def play_playlist(self, playlist_name):
        """
        Start playback on specified playlist

        Args:
            playlist_name (str): playlist name
        """
        playlists = self._get_config_field("playlists")
        if playlist_name not in playlists:
            raise InvalidParameter(f'Playlist "{playlist_name}" does not exist')

        self._destroy_audio_player()
        self._create_audio_player(playlist_name)
        self._change_audio_player_status(pause=False, volume=70)

    def _create_audio_player(self, playlist_name=None, repeat=False, shuffle=False):
        """
        Create audio player on audioplayer application. New player is always paused. Please start playback manually

        Args:
            playlist_name (str): create player based on specified playlist. If None specified, default playlist is used
            repeat (bool): if True playlist will repeat indefinitely
            shuffle (bool): if True playlist will be shuffled when end of it is reached
        """
        self.logger.debug(
            "Create audio player playlist=%s repeat=%s shuffle=%s",
            playlist_name,
            repeat,
            shuffle,
        )
        if not self.has_audioplayer:
            self.logger.warning(
                "Audioplayer application not installed. Unable to play music"
            )
            return

        tracks = (
            self._get_playlist_tracks(playlist_name)
            if playlist_name
            else self._get_default_playlist_tracks()
        )
        self.logger.debug("Playlist tracks: %s", tracks)
        if len(tracks) == 0:
            self.logger.warning(
                "Unable to create player because there is no default playlist or it is empty"
            )
            return

        if self.playback["playeruuid"]:
            self.send_command_advanced(
                "stop_playback",
                "audioplayer",
                {
                    "player_uuid": self.playback["playeruuid"],
                },
            )

        # create player sending first track
        track = tracks.pop(0)
        self.playback["playeruuid"] = self.send_command_advanced(
            "start_playback",
            "audioplayer",
            {
                "resource": track,
                "paused": True,
                "repeat": repeat,
                "shuffle": shuffle,
            },
        )
        if not self.playback["playeruuid"]:
            self.logger.warning(
                "No audio player created. It won't be able to play music"
            )
            return
        self.playback["playlistname"] = (
            playlist_name if playlist_name else self._get_config_field("default")
        )

        # fill playlist
        audioplayer_tracks = [
            {"resource": track, "audio_format": None} for track in tracks
        ]
        self.send_command_advanced(
            "add_tracks",
            "audioplayer",
            {
                "player_uuid": self.playback["playeruuid"],
                "tracks": audioplayer_tracks,
            },
        )

    def _destroy_audio_player(self):
        """
        Destroy current audio player if any
        """
        self.logger.debug("Destroy audio player")
        if not self.playback["playeruuid"]:
            return

        self.send_command_advanced(
            "stop_playback",
            "audioplayer",
            {
                "player_uuid": self.playback["playeruuid"],
            },
        )

    def _get_default_playlist_tracks(self):
        """
        Returns tracks for default playlist or empty track list if no default playlist defined

        Returns:
            list: list of tracks::

                [ path1 (str), path2 (str), ... ]

        """
        playlist_name = self._get_config_field("default")
        if not playlist_name:
            return []

        return self._get_playlist_tracks(playlist_name)

    def _get_playlist_tracks(self, playlist_name):
        """
        Get playlist tracks or empty list if playlist not found

        Args:
            playlist_name (str): playlist name

        Returns:
            list: list of tracks::

                [ path1 (str), path2 (str), ... ]

        """
        playlists = self._get_config_field("playlists")
        if not playlist_name in playlists:
            self.logger.debug('Playlist "%s" not found', playlist_name)
            return []

        return [
            file_["path"]
            for file_ in self.files
            for playlist_filename in playlists[playlist_name]
            if playlist_filename == file_["filename"]
        ]

    def _start_alarm(self, volume, repeat, shuffle):
        """
        Start alarm event launching default playlist playback

        Args:
            volume (int): player volume
            repeat (bool): True to create player with playlist repeat option
            shuffle (bool): True to create player with playlist shuffle option
        """
        self.logger.debug(
            "Start alarm vol=%s repeat=%s shuffle=%s", volume, repeat, shuffle
        )
        if not self.playback["playeruuid"]:
            self._create_audio_player(repeat=repeat, shuffle=shuffle)

        self._change_audio_player_status(pause=False, volume=volume)

    def _stop_alarm(self, snoozed=False):
        """
        Stop current alarm

        Args:
            snoozed (bool): True if snoozed was triggered and player must be paused instead of stopped
        """
        self.logger.debug("Stop alarm snoozed=%s", snoozed)
        if not self.playback["playeruuid"]:
            self.logger.warning(
                "Unable to stop alarm for non exiting or deleted player"
            )
            return

        if snoozed:
            self._change_audio_player_status(pause=True)
        else:
            self._destroy_audio_player()

    def _change_audio_player_status(self, pause, volume=None):
        """
        Change audio player playback. A player must have been created before!
        If previous playlist name match with latest played, track will be restored

        Args:
            pause (bool): True to pause playback, False to start playback
            volume (int): if specified set volume
        """
        self.logger.debug("Change audio player status pause=%s vol=%s", pause, volume)
        if not self.playback["playeruuid"]:
            self.logger.warning(
                "Unable to change audio player status because no player has been created"
            )
            return

        self.logger.debug("playback: %s", self.playback)
        params = {
            "player_uuid": self.playback["playeruuid"],
            "force_pause": pause,
            "force_play": not pause,
        }
        if volume is not None:
            params["volume"] = volume
        player_status = self.send_command_advanced(
            "pause_playback", "audioplayer", params
        )
        self.logger.info("Audio player playback is now %s", player_status)
