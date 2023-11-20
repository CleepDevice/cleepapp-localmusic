/**
 * Localmusic config component
 * Handle localmusic application configuration
 * If your application doesn't need configuration page, delete this file and its references into desc.json
 */
angular
.module('Cleep')
.directive('localmusicConfigComponent', ['$rootScope', 'cleepService', 'toastService', 'localmusicService', '$mdDialog',
function($rootScope, cleepService, toastService, localmusicService, $mdDialog) {

    var localmusicConfigController = function($scope) {
        var self = this;
        self.config = {};
        self.tabIndex = 'playlists';
        self.playlists = [];
        self.hasPlaylists = false;
        self.uploadFile = null;
        self.files = [];
        self.availableFiles = [];
        self.playlistTracks = [];
        self.playlistName = '';
        self.oldPlaylistName = '';
        self.playlistUpdate = false;

        self.$onInit = function() {
            cleepService.getModuleConfig('localmusic');
            self.getMusicFiles();
        };

        self.getMusicFiles = function() {
            localmusicService.getMusicFiles()
                .then(resp => {
                    self.setFiles(resp.data);
                });
        };

        self.setFiles = function (files) {
            self.files = [];
            for (const file of files.sort(self._sortFiles)) {
                self.files.push({
                    title: file.filename,
                    icon: 'music-circle-outline',
                    clicks: [
                        { icon: 'delete', style: 'md-accent', tooltip: 'Delete file', click: self.deleteMusicFile, meta: { filename: file.filename }},
                    ],
                });
            }
        };

        self.deleteMusicFile = function(filename) {
            localmusicService.deleteMusicFile(filename)
                .then(resp => {
                    toastService.success('File deleted');
                    self.getMusicFiles();
                });
        };

        self.addMusicFile = function (file) {
            if (!file) {
                return;
            }
                
            toastService.loading('Adding music file...');
            localmusicService.addMusicFile(file)
                .then((resp) => {
                    if (resp.data) {
                        toastService.success('Music file added');
                        self.getMusicFiles();
                    }
                });
        };

        self.openPlaylistDialog = function(playlistName, playlistTracks) {
            self.availableFiles = self.files.slice();
            if (angular.isUndefined(playlistName)) {
                self.playlistName = '';
                self.playlistTracks = [];
                self.playlistUpdate = false;
            } else {
                self.playlistName = self.oldPlaylistName = playlistName;
                self.playlistTracks = playlistTracks.map(track => {
                    const fileIndex = self.availableFiles.findIndex(file => track === file.title);
                    if (fileIndex >= 0) {
                        return self.availableFiles.splice(fileIndex, 1)[0];
                    }
                    return undefined;
                });
                self.playlistUpdate = true;
            }

            return $mdDialog.show({
                controller: function() { return self; },
                controllerAs: '$ctrl',
                templateUrl: 'playlist.dialog.html',
                parent: angular.element(document.body),
                clickOutsideToClose: false,
                fullscreen: true,
            });
        };

        self.cancelDialog = function() {
            $mdDialog.cancel();
        };

        self._sortFiles = function(a, b) {
			if (a.filename > b.filename) return 1;
    		if (b.filename > a.filename) return -1;
    		return 0;
        };

        self.moveRight = function(file) {
            self.playlistTracks.push(file);
            const fileIndex = self.availableFiles.findIndex((item) => item.title === file.title);
            self.availableFiles.splice(fileIndex, 1);
            self.availableFiles.sort(self._sortFiles);
        };

        self.moveLeft = function(track) {
            self.availableFiles.push(track);
            const trackIndex = self.playlistTracks.findIndex((item) => item.title === track.title);
            self.playlistTracks.splice(trackIndex, 1);
            self.availableFiles.sort(self._sortFiles);
        };

        self.moveUp = function(track) {
            const trackIndex = self.playlistTracks.findIndex((item) => item.title === track.title);
            if (trackIndex === 0) {
                return;
            }

            const trackElement = self.playlistTracks.splice(trackIndex, 1);
            self.playlistTracks.splice(trackIndex-1, 0, trackElement[0]);
        };

        self.moveDown = function(track) {
            const trackIndex = self.playlistTracks.findIndex((item) => item.title === track.title);
            if (trackIndex === self.playlistTracks.length-1) {
                return;
            }

            const trackElement = self.playlistTracks.splice(trackIndex, 1);
            self.playlistTracks.splice(trackIndex+1, 0, trackElement[0]);
        };

        self.addPlaylist = function() {
            if (!self.playlistName || !self.playlistTracks.length) {
                toastService.error('Please fill playlist name and add tracks to playlist');
                return;
            }

            const playlistTracks = self.playlistTracks.map((track) => track.title);
            localmusicService.addPlaylist(self.playlistName, playlistTracks)
                .then((resp) => {
                    if (!resp.error) {
                        self.cancelDialog();
                        cleepService.reloadModuleConfig('localmusic');
                    }
                })
        };

        self.deletePlaylist = function(playlistName) {
            localmusicService.deletePlaylist(playlistName)
                .then((resp) => {
                    if (!resp.error) {
                        toastService.success('Playlist deleted');
                        cleepService.reloadModuleConfig('localmusic');
                    }
                });
        };

        self.updatePlaylist = function() {
            if (!self.playlistName || !self.playlistTracks.length) {
                toastService.error('Please fill playlist name and add tracks to playlist');
                return;
            }

            const playlistTracks = self.playlistTracks.map((track) => track.title);
            localmusicService.updatePlaylist(self.oldPlaylistName, self.playlistName, playlistTracks)
                .then((resp) => {
                    if (!resp.error) {
                        self.cancelDialog();
                        cleepService.reloadModuleConfig('localmusic');
                    }
                });
        };

        self.setDefaultPlaylist = function(playlistName) {
            localmusicService.setDefaultPlaylist(playlistName)
                .then((resp) => {
                    if (!resp.error) {
                        toastService.success('Default playlist saved');
                        cleepService.reloadModuleConfig('localmusic');
                    }
                });
        };

        self.playPlaylist = function(playlistName) {
            localmusicService.playPlaylist(playlistName)
                .then((resp) => {
                    if (resp.error) {
                        toastService.error('Error occured starting playback');
                    }
                });
        };

        self.setPlaylists = function(playlists, defaultPlaylist) {
            self.playlists = [];
            for (const [playlistName, playlistTracks] of Object.entries(playlists)) {
                const icon = playlistName === defaultPlaylist ? 'playlist-star' : 'playlist-music-outline';
                const style = playlistName === defaultPlaylist ? 'md-accent' : '';
                const defaultSubtitle = playlistName === defaultPlaylist ? 'Default playlist - ' : '';
                self.playlists.push({
                    icon,
                    style,
                    title: playlistName,
                    subtitle: defaultSubtitle + playlistTracks.length + ' tracks',
                    clicks: [
                        { icon: 'play', tooltip: 'Play tracks', click: self.playPlaylist, meta: { playlistName } },
                        { icon: 'playlist-edit', tooltip: 'Edit playlist', click: self.openPlaylistDialog, meta: { playlistName, playlistTracks } },
                        { icon: 'playlist-star', tooltip: 'Set playlist as default', click: self.setDefaultPlaylist, meta: { playlistName } },
                        { icon: 'delete', tooltip: 'Delete playlist', style: 'md-accent', click: self.deletePlaylist, meta: { playlistName } },
                    ],
                });
            }
        };

        $rootScope.$watchCollection(
            () => cleepService.modules['localmusic'].config,
            (config) => {
                if (config && Object.keys(config).length) {
                    self.setPlaylists(config.playlists, config.default);
                    Object.assign(self.config, config);
                    self.hasPlaylists = self.playlists.length > 0;
                }
            },
        );
    };

    return {
        templateUrl: 'localmusic.config.html',
        replace: true,
        scope: true,
        controller: localmusicConfigController,
        controllerAs: '$ctrl',
    };
}]);
