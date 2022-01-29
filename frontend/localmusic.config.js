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
                    cleepService.syncVar(self.files, resp.data);
                    self.files.sort(self._sortFiles);
                });
        };

        self.deleteMusicFile = function(filename) {
            localmusicService.deleteMusicFile(filename)
                .then(resp => {
                    toastService.success('File deleted');
                    self.getMusicFiles();
                });
        };

        self.playlistDialog = function(playlistName, playlistTracks) {
            self.availableFiles = self.files.slice();
            if (angular.isUndefined(playlistName)) {
                self.playlistName = '';
                self.playlistTracks = [];
                self.playlistUpdate = false;
            } else {
                self.playlistName = self.oldPlaylistName = playlistName;
                self.playlistTracks = self.files.filter(file => {
                    var exists = Boolean(playlistTracks.find(track => track === file.filename))
                    if (exists) {
                        var index = self.availableFiles.findIndex(availableFile => availableFile.filename === file.filename);
                        if (index >= 0) self.availableFiles.splice(index, 1);
                    }
                    return exists;
                });
                self.playlistUpdate = true;
            }

            return $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'localmusicCtl',
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
            self.availableFiles.splice(self.availableFiles.indexOf(file), 1);
            self.playlistTracks.sort(self._sortFiles);
            self.availableFiles.sort(self._sortFiles);
        };

        self.moveLeft = function(track) {
            self.availableFiles.push(track);
            self.playlistTracks.splice(self.playlistTracks.indexOf(track), 1);
            self.playlistTracks.sort(self._sortFiles);
            self.availableFiles.sort(self._sortFiles);
        };

        self.addPlaylist = function() {
            if (!self.playlistName || !self.playlistTracks.length) {
                toastService.error('Please fill playlist name and add tracks to playlist');
                return;
            }

            var playlistTracks = self.playlistTracks.map((track) => track.filename);

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

            var playlistTracks = self.playlistTracks.map((track) => track.filename);

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

        $scope.$watch(function() {
            return self.uploadFile;
        }, function(file) {
            if (file) {
                localmusicService.addMusicFile(file)
                .then((resp) => {
                    if (resp.data) {
                        toastService.success('Music file added');
                        self.getMusicFiles();
                    }
                });
            }
        });

        $rootScope.$watch(function() {
            return cleepService.modules['localmusic'].config;
        }, function(newVal, oldVal) {
            if(newVal && Object.keys(newVal).length) {
                Object.assign(self.config, newVal);
                self.hasPlaylists = Object.keys(self.config.playlists).length > 0;
            }
        });

    };

    return {
        templateUrl: 'localmusic.config.html',
        replace: true,
        scope: true,
        controller: localmusicConfigController,
        controllerAs: 'localmusicCtl',
    };
}]);
