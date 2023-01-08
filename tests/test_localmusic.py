#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import logging
import sys
sys.path.append('../')
from backend.localmusic import Localmusic
from cleep.exception import InvalidParameter, MissingParameter, CommandError, Unauthorized
from cleep.libs.tests import session
from mock import Mock, patch
from copy import deepcopy
from cleep.libs.tests.common import get_log_level

PLAYLISTS = {
    "playlist1": [
        "file1.mp3",
        "file2.mp3",
        "file3.mp3"
    ],
    "playlist2": [
        "file2.mp3"
    ]
}
FILES = [
    {'filename': 'file1.mp3', 'path': '/opt/module/localmusic/file1.mp3'},
    {'filename': 'file2.mp3', 'path': '/opt/module/localmusic/file2.mp3'},
    {'filename': 'file3.mp3', 'path': '/opt/module/localmusic/file3.mp3'},
]
LOG_LEVEL = get_log_level()

class TestLocalmusic(unittest.TestCase):

    def setUp(self):
        logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')
        self.session = session.TestSession(self)

    def tearDown(self):
        # clean session
        self.session.clean()

    def init(self, start=True):
        """
        Call this function at beginning of every test cases. By default it starts your app, but if you specify start=False,
        the application must be started manually which is useful in some cases like testing _on_configure app function.
        """
        self.module = self.session.setup(Localmusic)

        cmd = self.session.make_mock_command('is_module_loaded', True)
        self.session.add_mock_command(cmd)

        if start:
            self.session.start_module(self.module)

    def test_configure(self):
        self.init(False)
        self.module._refresh_music_files = Mock()
        self.module._check_playlists = Mock()

        self.session.start_module(self.module)

        self.module._refresh_music_files.assert_called()
        self.module._check_playlists.assert_called()

    def test__on_start(self):
        self.init(False)
        self.module.is_module_loaded = Mock()

        self.session.start_module(self.module)

        self.module.is_module_loaded.assert_called_with('audioplayer')

    def test_on_event_update_playing_track(self):
        self.init()
        self.module.playback = {
            "playeruuid": "uuid",
            "index": 0,
        }
        event = {
            "event": "audioplayer.playback.update",
            "params": {
                "playeruuid": "uuid",
                "state": "playing",
                "index": 1,
            }
        }

        self.module.on_event(event)

        self.assertEqual(self.module.playback.get("index"), 1)

    def test_on_event_playback_stopped(self):
        self.init()
        self.module.playback = {
            "playeruuid": "uuid",
            "index": 0,
        }
        event = {
            "event": "audioplayer.playback.update",
            "params": {
                "playeruuid": "uuid",
                "state": "stopped",
                "index": 1,
            }
        }

        self.module.on_event(event)

        self.assertEqual(self.module.playback.get("playeruuid"), None)

    def test_on_event_not_player(self):
        self.init()
        self.module.playback = {
            "playeruuid": "uuid",
            "index": 4,
        }
        event = {
            "event": "audioplayer.playback.update",
            "params": {
                "playeruuid": "otheruuid",
                "state": "stopped",
                "index": 1,
            }
        }

        self.module.on_event(event)

        self.assertEqual(self.module.playback.get("playeruuid"), "uuid")
        self.assertEqual(self.module.playback.get("index"), 4)

    def test_on_render_with_alarmprofile_triggered(self):
        self.init()
        self.module._start_alarm = Mock()
        self.module._stop_alarm = Mock()
        
        self.module.on_render('AlarmProfile', {'status': 'triggered', 'volume': 66, 'repeat': True, 'shuffle': False})

        self.module._start_alarm.assert_called_with(66, True, False)
        self.module._stop_alarm.assert_not_called()

    def test_on_render_with_alarmprofile_stopped(self):
        self.init()
        self.module._start_alarm = Mock()
        self.module._stop_alarm = Mock()
        
        self.module.on_render('AlarmProfile', {'status': 'stopped', 'volume': 66, 'repeat': True, 'shuffle': False})

        self.module._start_alarm.assert_not_called()
        self.module._stop_alarm.assert_called_with(False)

    def test_on_render_with_alarmprofile_snoozed(self):
        self.init()
        self.module._start_alarm = Mock()
        self.module._stop_alarm = Mock()
        
        self.module.on_render('AlarmProfile', {'status': 'snoozed', 'volume': 66, 'repeat': True, 'shuffle': False})

        self.module._start_alarm.assert_not_called()
        self.module._stop_alarm.assert_called_with(True)

    def test_on_render_with_alarmprofile_scheduled(self):
        self.init()
        self.module._start_alarm = Mock()
        self.module._stop_alarm = Mock()

        self.module.on_render('AlarmProfile', {'status': 'scheduled', 'volume': 66, 'repeat': True, 'shuffle': False})
        
        self.module._start_alarm.assert_not_called()
        self.module._stop_alarm.assert_not_called()

    def test_on_render_with_alarmprofile_unscheduled(self):
        self.init()
        self.module._start_alarm = Mock()
        self.module._stop_alarm = Mock()

        self.module.on_render('AlarmProfile', {'status': 'unscheduled', 'volume': 66, 'repeat': True, 'shuffle': False})
        
        self.module._start_alarm.assert_not_called()
        self.module._stop_alarm.assert_not_called()

    def test_on_render_with_dummyprofile(self):
        self.init()
        self.module._start_alarm = Mock()
        self.module._stop_alarm = Mock()

        self.module.on_render('DummyProfile', {'status': 'scheduled', 'volume': 66})
        
        self.module._start_alarm.assert_not_called()
        self.module._stop_alarm.assert_not_called()

    def test__refresh_music_files(self):
        self.init()

        with patch('backend.localmusic.os.walk') as walk_mock:
            walk_mock.return_value = [
                ('/opt/module/localmusic', (), ('file1.mp3', 'file2.mp3')),
            ]
            self.module._refresh_music_files()
            logging.debug('Files: %s', self.module.files)

            self.assertListEqual(self.module.files, [
                {'filename': 'file1.mp3', 'path': '/opt/module/localmusic/file1.mp3'},
                {'filename': 'file2.mp3', 'path': '/opt/module/localmusic/file2.mp3'}
            ])

    def test__check_playlists(self):
        self.init()
        self.module._get_config_field = Mock(return_value=deepcopy(PLAYLISTS))
        files = deepcopy(FILES)
        files.pop(1)
        self.module.files = files
        self.module._set_config_field = Mock()
        
        self.module._check_playlists()

        self.module._set_config_field.assert_called_with('playlists', {'playlist1': ['file1.mp3', 'file3.mp3']})

    def test__check_playlists_with_parameters(self):
        self.init()
        files = deepcopy(FILES)
        files.pop(1)
        self.module.files = files
        self.module._set_config_field = Mock()
        
        self.module._check_playlists(deepcopy(PLAYLISTS))

        self.module._set_config_field.assert_called_with('playlists', {'playlist1': ['file1.mp3', 'file3.mp3']})

    def test_get_music_files(self):
        self.init()
        self.module.files = deepcopy(FILES)

        files = self.module.get_music_files()

        self.assertListEqual(files, FILES)

    def test_get_playback(self):
        self.init()

        playback = self.module.get_playback()

        self.assertEqual(playback, {
            "index": None,
            "playeruuid": None,
            "playlistname": None,
        })

    def test_add_music_file(self):
        self.init()
        self.module._refresh_music_files = Mock()

        with patch('backend.localmusic.os.path.exists') as exists_mock:
            exists_mock.return_value = False
            result = self.module.add_music_file('dummy.mp3')

            self.assertTrue(result)
            self.module._refresh_music_files.assert_called()

    @patch('backend.localmusic.Localmusic.ALLOWED_MUSIC_EXTENSIONS', ['mp3', 'ogg'])
    def test_add_music_file_invalid_extension(self):
        self.init()

        with self.assertRaises(InvalidParameter) as cm:
            result = self.module.add_music_file('dummy.wav')
        self.assertEqual(str(cm.exception), 'Invalid file extension (only mp3,ogg allowed)')

    def test_add_music_file_already_exists(self):
        self.init()

        with patch('backend.localmusic.os.path.exists') as exists_mock:
            exists_mock.return_value = True
            with self.assertRaises(CommandError) as cm:
                result = self.module.add_music_file('dummy.mp3')
            self.assertEqual(str(cm.exception), 'Music file "dummy.mp3" already exists')

    def test_add_music_file_unable_to_save(self):
        self.init()

        with patch('backend.localmusic.os.path.exists') as exists_mock:
            exists_mock.return_value = False
            self.module.cleep_filesystem.move.return_value = False
            with self.assertRaises(CommandError) as cm:
                result = self.module.add_music_file('dummy.mp3')
            self.assertEqual(str(cm.exception), 'Unable to save "dummy.mp3"')

    def test_delete_music_file(self):
        self.init()
        self.module._refresh_music_file = Mock()
        self.module.cleep_filesystem.rm.return_value = True

        with patch('backend.localmusic.os.walk') as walk_mock:
            walk_mock.return_value = [
                ('/opt/module/localmusic', (), ('file1.mp3', 'file2.mp3', 'file3.mp3')),
            ]

            self.module.delete_music_file('file2.mp3')

            self.module.cleep_filesystem.rm.assert_called_with('/opt/module/localmusic/file2.mp3')
            self.module._refresh_music_file.assert_not_called()

    def test_delete_music_file_file_not_found(self):
        self.init()
        self.module._refresh_music_file = Mock()
        self.module.cleep_filesystem.rm.return_value = True

        with patch('backend.localmusic.os.walk') as walk_mock:
            walk_mock.return_value = [
                ('/opt/module/localmusic', (), ('file1.mp3', 'file2.mp3', 'file3.mp3')),
            ]

            with self.assertRaises(InvalidParameter) as cm:
                self.module.delete_music_file('file4.mp3')
            self.assertEqual(str(cm.exception), 'File "file4.mp3" was not found')

    def test_delete_music_file_unable_to_delete(self):
        self.init()
        self.module._refresh_music_file = Mock()
        self.module.cleep_filesystem.rm.return_value = False

        with patch('backend.localmusic.os.walk') as walk_mock:
            walk_mock.return_value = [
                ('/opt/module/localmusic', (), ('file1.mp3', 'file2.mp3', 'file3.mp3')),
            ]

            with self.assertRaises(CommandError) as cm:
                self.module.delete_music_file('file2.mp3')
            self.assertEqual(str(cm.exception), 'Unable to delete "file2.mp3"')

    def test_add_playlist(self):
        self.init()
        self.module.files = deepcopy(FILES)
        self.module._get_config_field = Mock(return_value=deepcopy(PLAYLISTS))
        self.module._set_config_field = Mock()
        self.module._check_playlists = Mock()

        files = ['file1.mp3', 'file2.mp3']
        self.module.add_playlist('playlist3', files)

        playlists = deepcopy(PLAYLISTS)
        playlists['playlist3'] = files
        self.module._set_config_field.assert_called_with('playlists', playlists)
        self.module._check_playlists.assert_called()

    def test_add_playlist_first_add_set_default_playlist(self):
        self.init()
        self.module.files = deepcopy(FILES)
        self.module._get_config_field = Mock(return_value={})
        self.module._check_playlists = Mock()
        files = ['file1.mp3', 'file2.mp3']
        self.module.set_default_playlist = Mock()

        self.module.add_playlist('playlist3', files)

        self.module.set_default_playlist.assert_called_with('playlist3')

    def test_add_playlist_invalid_parameters(self):
        self.init()
        self.module.files = deepcopy(FILES)
        self.module._get_config_field = Mock(return_value=deepcopy(PLAYLISTS))

        with self.assertRaises(InvalidParameter) as cm:
            self.module.add_playlist('playlist3', [])
        self.assertEqual(str(cm.exception), 'Playlist must not be empty')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.add_playlist('', ['file1.mp3'])
        self.assertEqual(str(cm.exception), 'Parameter "playlist_name" is invalid (specified="")')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.add_playlist('playlist2', ['file1.mp3'])
        self.assertEqual(str(cm.exception), 'Playlist "playlist2" already exists')

    def test_update_playlist_update_files_only(self):
        self.init()
        self.module.files = deepcopy(FILES)
        self.module._get_config_field = Mock(return_value=deepcopy(PLAYLISTS))
        self.module._set_config_field = Mock()
        self.module._check_playlists = Mock()

        files = ['file1.mp3', 'file3.mp3']
        self.module.update_playlist('playlist2', 'playlist2', files)

        playlists = deepcopy(PLAYLISTS)
        playlists['playlist2'] = files
        self.module._set_config_field.assert_called_with('playlists', playlists)
        self.module._check_playlists.assert_called()

    def test_update_playlist_update_rename_playlist(self):
        self.init()
        self.module.files = deepcopy(FILES)
        self.module._get_config_field = Mock(return_value=deepcopy(PLAYLISTS))
        self.module._set_config_field = Mock()
        self.module._check_playlists = Mock()

        files = ['file1.mp3', 'file3.mp3']
        self.module.update_playlist('playlist2', 'playlist3', files)

        playlists = deepcopy(PLAYLISTS)
        del playlists['playlist2']
        playlists['playlist3'] = files
        logging.debug('Playlist: %s', playlists)
        self.module._set_config_field.assert_called_with('playlists', playlists)
        self.module._check_playlists.assert_called()

    def test_update_playlist_invalid_parameters(self):
        self.init()
        self.module.files = deepcopy(FILES)
        self.module._get_config_field = Mock(return_value=deepcopy(PLAYLISTS))

        with self.assertRaises(InvalidParameter) as cm:
            self.module.update_playlist('playlist3', 'playlist3', [])
        self.assertEqual(str(cm.exception), 'Playlist must not be empty')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.update_playlist('', '', ['file1.mp3'])
        self.assertEqual(str(cm.exception), 'Parameter "playlist_name" is invalid (specified="")')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.update_playlist('playlist4', 'playlist2', ['file1.mp3'])
        self.assertEqual(str(cm.exception), 'Playlist "playlist4" does not exist')

    def test_delete_playlist(self):
        self.init()
        self.module.files = deepcopy(FILES)
        self.module._get_config_field = Mock(return_value=deepcopy(PLAYLISTS))
        self.module._set_config_field = Mock()

        self.module.delete_playlist('playlist2')

        playlists = deepcopy(PLAYLISTS)
        del playlists['playlist2']
        self.module._set_config_field.assert_called_with('playlists', playlists)

    def test_delete_playlist_invalid_parameters(self):
        self.init()
        self.module.files = deepcopy(FILES)
        self.module._get_config_field = Mock(return_value=deepcopy(PLAYLISTS))

        with self.assertRaises(InvalidParameter) as cm:
            self.module.delete_playlist('playlist4')
        self.assertEqual(str(cm.exception), 'Playlist "playlist4" does not exist')

    def test_set_default_playlist(self):
        self.init()
        self.module.files = deepcopy(FILES)
        self.module._get_config_field = Mock(return_value=deepcopy(PLAYLISTS))
        self.module._set_config_field = Mock()

        self.module.set_default_playlist('playlist2')

        self.module._set_config_field.assert_called_with('default', 'playlist2')

    def test_set_default_playlist_invalid_parameters(self):
        self.init()
        self.module.files = deepcopy(FILES)
        self.module._get_config_field = Mock(return_value=deepcopy(PLAYLISTS))

        with self.assertRaises(InvalidParameter) as cm:
            self.module.set_default_playlist('playlist4')
        self.assertEqual(str(cm.exception), 'Playlist "playlist4" does not exist')

    def test_play_playlist(self):
        self.init()
        self.module._get_config_field = Mock(return_value=deepcopy(PLAYLISTS))
        self.module._destroy_audio_player = Mock()
        self.module._create_audio_player = Mock()
        self.module._change_audio_player_status = Mock()

        self.module.play_playlist("playlist2")

        self.module._destroy_audio_player.assert_called()
        self.module._create_audio_player.assert_called_with("playlist2")
        self.module._change_audio_player_status("playlist2", pause=False)

    def test_play_playlist_unknown_playlist(self):
        self.init()
        self.module._get_config_field = Mock(return_value=deepcopy(PLAYLISTS))
        self.module._destroy_audio_player = Mock()
        self.module._create_audio_player = Mock()
        self.module._change_audio_player_status = Mock()

        with self.assertRaises(InvalidParameter) as cm:
            self.module.play_playlist("playlist666")
        self.assertEqual(str(cm.exception), 'Playlist "playlist666" does not exist')

        self.module._destroy_audio_player.assert_not_called()
        self.module._create_audio_player.assert_not_called()
        self.module._change_audio_player_status.assert_not_called()

    def test__create_audio_player_default_params(self):
        self.init()
        self.module.has_audioplayer = True
        start_playback_cmd = self.session.make_mock_command('start_playback', 'uuid')
        self.session.add_mock_command(start_playback_cmd)
        add_tracks_cmd = self.session.make_mock_command('add_tracks')
        self.session.add_mock_command(add_tracks_cmd)
        file1 = '/opt/cleep/modules/localmusic/file1.mp3'
        file2 = '/opt/cleep/modules/localmusic/file2.mp3'
        self.module._get_default_playlist_tracks = Mock(return_value=[file1, file2])

        self.module._create_audio_player()

        self.session.assert_command_called_with('start_playback', {"resource": file1, "paused": True, "repeat": False, "shuffle": False}, 'audioplayer')
        self.session.assert_command_called_with('add_tracks', {"player_uuid": "uuid", "tracks": [{"audio_format": None, "resource": file2}]}, 'audioplayer')

    def test__create_audio_player_custom_params(self):
        self.init()
        self.module.has_audioplayer = True
        start_playback_cmd = self.session.make_mock_command('start_playback', 'uuid')
        self.session.add_mock_command(start_playback_cmd)
        add_tracks_cmd = self.session.make_mock_command('add_tracks')
        self.session.add_mock_command(add_tracks_cmd)
        file1 = '/opt/cleep/modules/localmusic/file1.mp3'
        file2 = '/opt/cleep/modules/localmusic/file2.mp3'
        self.module._get_playlist_tracks = Mock(return_value=[file1, file2])

        self.module._create_audio_player(playlist_name="default", repeat=True, shuffle=True)

        self.session.assert_command_called_with('start_playback', {"resource": file1, "paused": True, "repeat": True, "shuffle": True}, 'audioplayer')
        self.session.assert_command_called_with('add_tracks', {"player_uuid": "uuid", "tracks": [{"audio_format": None, "resource": file2}]}, 'audioplayer')

    def test__create_audio_player_with_existing_audioplayer(self):
        self.init()
        self.module.has_audioplayer = True
        start_playback_cmd = self.session.make_mock_command('start_playback', 'uuid')
        self.session.add_mock_command(start_playback_cmd)
        stop_playback_cmd = self.session.make_mock_command('stop_playback', 'uuid')
        self.session.add_mock_command(stop_playback_cmd)
        add_tracks_cmd = self.session.make_mock_command('add_tracks')
        self.session.add_mock_command(add_tracks_cmd)
        file1 = '/opt/cleep/modules/localmusic/file1.mp3'
        file2 = '/opt/cleep/modules/localmusic/file2.mp3'
        self.module._get_default_playlist_tracks = Mock(return_value=[file1, file2])
        self.module.playback = {
            "playeruuid": "uuid"
        }

        self.module._create_audio_player()

        self.session.assert_command_called_with('start_playback', {"resource": file1, "paused": True, "repeat": False, "shuffle": False}, 'audioplayer')
        self.session.assert_command_called_with('add_tracks', {"player_uuid": "uuid", "tracks": [{"audio_format": None, "resource": file2}]}, 'audioplayer')
        self.session.assert_command_called_with('stop_playback', {"player_uuid": "uuid"})

    def test__create_audio_player_failed_to_create_player(self):
        self.init()
        self.module.has_audioplayer = True
        start_playback_cmd = self.session.make_mock_command('start_playback', None)
        self.session.add_mock_command(start_playback_cmd)
        add_tracks_cmd = self.session.make_mock_command('add_tracks')
        self.session.add_mock_command(add_tracks_cmd)
        file1 = '/opt/cleep/modules/localmusic/file1.mp3'
        file2 = '/opt/cleep/modules/localmusic/file2.mp3'
        self.module._get_default_playlist_tracks = Mock(return_value=[file1, file2])

        self.module._create_audio_player()

        self.assertEqual(self.session.command_call_count('add_tracks'), 0)

    def test__create_audio_player_no_audioplayer_app(self):
        self.init()
        self.module.has_audioplayer = False
        start_playback_cmd = self.session.make_mock_command('start_playback', 'uuid')
        self.session.add_mock_command(start_playback_cmd)

        self.module._create_audio_player()

        self.assertEqual(self.session.command_call_count('start_playback'), 0)

    def test__create_audio_player_only_one_track_in_playlist(self):
        self.init()
        self.module.has_audioplayer = True
        start_playback_cmd = self.session.make_mock_command('start_playback', 'uuid')
        self.session.add_mock_command(start_playback_cmd)
        add_tracks_cmd = self.session.make_mock_command('add_tracks')
        self.session.add_mock_command(add_tracks_cmd)
        file1 = '/opt/cleep/modules/localmusic/file1.mp3'
        self.module._get_default_playlist_tracks = Mock(return_value=[file1])

        self.module._create_audio_player()

        self.session.assert_command_called_with('start_playback', {"resource": file1, "paused": True, "repeat": False, "shuffle": False}, 'audioplayer')
        self.assertEqual(self.session.command_call_count('add_tracks'), 1)

    def test__create_audio_player_no_track_in_playlist(self):
        self.init()
        self.module.has_audioplayer = True
        start_playback_cmd = self.session.make_mock_command('start_playback', 'uuid')
        self.session.add_mock_command(start_playback_cmd)
        add_tracks_cmd = self.session.make_mock_command('add_tracks')
        self.session.add_mock_command(add_tracks_cmd)
        self.module._get_default_playlist_tracks = Mock(return_value=[])

        self.module._create_audio_player()

        self.session.assert_command_not_called('start_playback')

    def test__destroy_audio_player(self):
        self.init()
        stop_playback_cmd = self.session.make_mock_command('stop_playback')
        self.session.add_mock_command(stop_playback_cmd)
        self.module.playback = {
            "playeruuid": "uuid",
            "index": 0,
            "playlistname": "playlist1",
        }

        self.module._destroy_audio_player()

        self.session.assert_command_called_with('stop_playback', {"player_uuid": "uuid"})

    def test__destroy_audio_player_no_player_uuid(self):
        self.init()
        stop_playback_cmd = self.session.make_mock_command('stop_playback')
        self.session.add_mock_command(stop_playback_cmd)
        self.module.playback = {
            "playeruuid": None,
            "index": 0,
            "playlistname": "playlist1",
        }

        self.module._destroy_audio_player()

        self.session.assert_command_not_called('stop_playback')

    def test__get_default_playlist_tracks(self):
        self.init()
        self.module.files = deepcopy(FILES)
        playlists = deepcopy(PLAYLISTS)
        self.module._get_config_field = Mock(side_effect=["playlist2", playlists])

        tracks = self.module._get_default_playlist_tracks()
        logging.debug('Tracks: %s', tracks)

        self.assertListEqual(tracks, ['/opt/module/localmusic/file2.mp3'])

    def test__get_default_playlist_tracks_no_default_playlist(self):
        self.init()
        self.module.files = deepcopy(FILES)
        self.module._get_config_field = Mock(side_effect=[None])

        tracks = self.module._get_default_playlist_tracks()
        logging.debug('Tracks: %s', tracks)

        self.assertListEqual(tracks, [])

    def test__get_playlist_tracks(self):
        self.init()
        self.module.files = deepcopy(FILES)
        playlists = deepcopy(PLAYLISTS)
        self.module._get_config_field = Mock(side_effect=[playlists])

        tracks = self.module._get_playlist_tracks("playlist2")

        self.assertEqual(tracks, ["/opt/module/localmusic/file2.mp3"])

    def test__get_playlist_tracks_playlist_not_found(self):
        self.init()
        self.module.files = deepcopy(FILES)
        playlists = deepcopy(PLAYLISTS)
        self.module._get_config_field = Mock(side_effect=[playlists])

        tracks = self.module._get_playlist_tracks("playlist3")

        self.assertEqual(tracks, [])

    def test__start_alarm_with_existing_player(self):
        self.init()
        self.module.has_audioplayer = True
        self.module.playback["playeruuid"] = "uuid"
        self.module._change_audio_player_status = Mock()
    
        self.module._start_alarm(12, False, False)

        self.module._change_audio_player_status.assert_called_with(pause=False, volume=12)

    def test__start_alarm_should_create_player(self):
        self.init()
        self.module.has_audioplayer = True
        self.module.playback["playeruuid"] = None
        self.module._change_audio_player_status = Mock()
        self.module._create_audio_player = Mock()

        self.module._start_alarm(12, False, True)

        self.module._create_audio_player.assert_called_with(repeat=False, shuffle=True)

    def test__stop_alarm_snoozed_disabled(self):
        self.init()
        self.module.playback["playeruuid"] = "uuid"
        self.module._destroy_audio_player = Mock()
        self.module._change_audio_player_status = Mock()

        self.module._stop_alarm(False)

        self.module._destroy_audio_player.assert_called()
        self.module._change_audio_player_status.assert_not_called()

    def test__stop_alarm_snoozed_enabled(self):
        self.init()
        self.module.playback["playeruuid"] = "uuid"
        self.module._destroy_audio_player = Mock()
        self.module._change_audio_player_status = Mock()

        self.module._stop_alarm(True)

        self.module._destroy_audio_player.assert_not_called()
        self.module._change_audio_player_status.assert_called_with(pause=True)

    def test__stop_alarm_no_player(self):
        self.init()
        self.module.playback["playeruuid"] = None
        self.module._destroy_audio_player = Mock()
        self.module._change_audio_player_status = Mock()

        self.module._stop_alarm(False)

        self.module._destroy_audio_player.assert_not_called()
        self.module._change_audio_player_status.assert_not_called()

    def test__change_audio_player_status_start_playback(self):
        self.init()
        self.module.playback["playeruuid"] = "uuid"
        pause_playback_cmd = self.session.make_mock_command('pause_playback')
        self.session.add_mock_command(pause_playback_cmd)

        self.module._change_audio_player_status(pause=False, volume=50)

        self.session.assert_command_called_with("pause_playback", {"player_uuid": "uuid", "force_pause": False, "force_play": True, "volume": 50})

    def test__change_audio_player_status_start_playback_without_volume(self):
        self.init()
        self.module.playback["playeruuid"] = "uuid"
        pause_playback_cmd = self.session.make_mock_command('pause_playback')
        self.session.add_mock_command(pause_playback_cmd)

        self.module._change_audio_player_status(pause=False)

        self.session.assert_command_called_with("pause_playback", {"player_uuid": "uuid", "force_pause": False, "force_play": True})

    def test__change_audio_player_status_pause_playback(self):
        self.init()
        self.module.playback["playeruuid"] = "uuid"
        pause_playback_cmd = self.session.make_mock_command('pause_playback')
        self.session.add_mock_command(pause_playback_cmd)

        self.module._change_audio_player_status(pause=True, volume=50)

        self.session.assert_command_called_with("pause_playback", {"player_uuid": "uuid", "force_pause": True, "force_play": False, "volume": 50})

    def test__change_audio_player_no_player(self):
        self.init()
        self.module.playback["playeruuid"] = None
        pause_playback_cmd = self.session.make_mock_command('pause_playback')
        self.session.add_mock_command(pause_playback_cmd)

        self.module._change_audio_player_status(pause=True)

        self.session.assert_command_not_called("pause_playback")


if __name__ == '__main__':
    unittest.main()
    
