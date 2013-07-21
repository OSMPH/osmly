osmly.connect = (function(){
    var connect = {};

    connect.submitToServer = function(result) {
        var url = osmly.settings.featuresApi + 'db=' + osmly.settings.db +
            '&id=' + osmly.item.id + '&action=problem';
        $.ajax({
            type: 'POST',
            url: url,
            crossDomain: true,
            data: {problem: result, user: osmly.user.name}
        });
        // no callback, not worth slowing down/complicating over, it's reproducable
    };

    connect.openChangeset = function(id, callback) {
        if (!id){createChangeset(callback);}
        osmly.ui.notify('checking changeset status');

        $.ajax({
            url: osmly.settings.writeApi + '/api/0.6/changeset/' + id,
            cache: false
        }).done(function(xml) {
            var cs = xml.getElementsByTagName('changeset');
            if (cs[0].getAttribute('open') === 'true') {
                callback();
            } else {
                createChangeset(callback);
            }
        });
    };

    function createChangeset(callback) {
        var url = osmly.settings.writeApi + '/api/0.6/changeset/create',
            token_secret = osmly.token('secret'),
            change = newChangesetXml();

        osmly.ui.notify('creating a new changeset');

        // removed ohauth
    }

    function newChangesetXml() {
        var tags = '';
        for (var c = 0; i < osmly.settings.changesetTags.length; c++) {
            tags +=
                '<tag k="' + osmly.settings.changesetTags[c][0] +
                '" v="' + osmly.settings.changesetTags[c][1] + '"/>';
        }
        return '<osm><changeset>' + tags + '<\/changeset><\/osm>';
    }

    function submitToOSM() {
        var id = osmly.token('changeset_id');
        $('#changeset').fadeIn(500);
        $('#changeset-link')
            .html('<a href="' + osmly.settings.writeApi + '/browse/changeset/' +
                id + '" target="_blank">Details on osm.org »</a>');

        var url = osmly.settings.writeApi + '/api/0.6/changeset/' + id + '/upload',
            token_secret = osmly.token('secret'),
            geojson = osmly.item.layer.toGeoJSON(),
            osmChange = toOsmChange(geojson);

        osmly.ui.notify('uploading to OSM');

        // removed ohauth
    }

    function toOsmChange(geojson) {
        return '<osmChange version="0.6" generator="osmly"><create>' +
            innerOsm(geojson) + '</create></osmChange>';
    }

    connect.request_oauth = function() {
        var url = osmly.settings.writeApi + '/oauth/request_token';

        // removed ohauth
    };

    // https://github.com/systemed/iD/blob/master/js/id/oauth.js#L107
    function access_oauth(oauth_token) {
        // removed ohauth
    }

    function getUserDetails() {
        // this is all pretty stupid, we just need the username
        // we're only using the username to link the user to their own profile
            // ~50 lines for one link, a tiny convenience
        // probably removing soon
        var url = osmly.settings.writeApi + '/api/0.6/user/details',
            token_secret = osmly.token('secret');

        // removed ohauth
    }

    return connect;
}());
