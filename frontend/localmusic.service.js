/**
 * Localmusic service.
 * Handle localmusic application requests.
 * Service is the place to store your application content (it is a singleton) and
 * to provide your application functions.
 */
angular
.module('Cleep')
.service('localmusicService', ['$rootScope', 'rpcService',
function($rootScope, rpcService) {
    var self = this;

    self.getMusicFiles = function() {
        return rpcService.sendCommand('get_music_files', 'localmusic');
    };  

    self.addMusicFile = function(file) {
        return rpcService.upload('add_music_file', 'localmusic', file);
    };  

    self.deleteMusicFile = function(filename) {
        return rpcService.sendCommand('delete_music_file', 'localmusic', {
            filename: filename,
        }); 
    };

    self.addPlaylist = function(playlistName, files) {
        return rpcService.sendCommand('add_playlist', 'localmusic', {
            playlist_name: playlistName,
            files: files,
        }); 
    };

    self.deletePlaylist = function(playlistName) {
        return rpcService.sendCommand('delete_playlist', 'localmusic', {
            playlist_name: playlistName,
        }); 
    };

    self.updatePlaylist = function(playlistName, newPlaylistName, files) {
        return rpcService.sendCommand('update_playlist', 'localmusic', {
            playlist_name: playlistName,
            new_playlist_name: newPlaylistName,
            files: files,
        }); 
    };

    self.setDefaultPlaylist = function(playlistName) {
        return rpcService.sendCommand('set_default_playlist', 'localmusic', {
            playlist_name: playlistName,
        });
    };

    self.playPlaylist = function(playlistName) {
        return rpcService.sendCommand('play_playlist', 'localmusic', {
            playlist_name: playlistName,
        });
    };

}]);
