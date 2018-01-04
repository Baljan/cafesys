$(document).ready(function () {
    $('.init-hidden').css('visibility', 'visible').show();
    $('#nav .active').click();
    
    /* Semester View */
    $('body.semesters #id_start').change(function() {
        var dparts = $(this).attr('value').split('-'),
            sem = 'VT',
            val = '';
        if (5 < dparts[1]) sem = 'HT';
        if (dparts.length == 3) val = '' + sem + dparts[0];
        $('body.semesters #id_name').attr('value', val);
    });
    $('body.semesters .cancel').click(function() {
        history.go(-1);
    });
    



    /* Search Person View */
    if ($('body').hasClass('search-person')) {
        var uFormat = function(user) {
            var uName = user.fields.username,
                fName = user.fields.first_name,
                lName = user.fields.last_name;
            return ''+fName+' '+lName+' ('+uName+')';
        }

        var uLink = function(user) {
            var uName = user.fields.username;
            // FIXME: DRY, use get_absolute_url in some way
            var link = '/baljan/user/' + uName;
            return '<a href="' + link + '"/>';
        }

        var f = $('form.search'),
            terms = $('#search-terms'),
            ul = $('.results ul'),
            count = $('.results .count'),
            curSerial = '',
            curRequest = false;
        
        // These should be nice in JS-enabled browsers.
        terms.focus();
        f.attr('autocomplete', 'off');
        f.submit(function() { return false; });

        terms.bind('keyup', function() {
            var serial = f.serialize();
            if (curSerial == serial) return;
            if (curRequest) curRequest.abort();

            curRequest = $.ajax({
                data: serial,
                url: document.location.pathname, // f.attr('action') is empty string
                type: f.attr('method'),
                dataType: 'json',
                success: function(hits) {
                    if (!hits) return;
                    ul.html('');
                    count.html('' + hits.length);
                    var lis = false,
                        as = false,
                        delay = 0;

                    // This looks odd. With this code, the hit list is populated
                    // asynchronously.
                    var addTexts = {
                        delay: delay,
                        loop: function(i) {
                            $(this).text(uFormat(hits[i]));
                        }
                    }
                    var addLinks = {
                        delay: delay,
                        loop: function(i) {
                            $(this).html(uLink(hits[i]));
                        },
                        end: function() {
                            var as = lis.children('a');
                            as.eachAsync(addTexts);
                        }
                    }
                    $.eachAsync(hits, {
                        delay: delay,
                        loop: function() {
                            ul.append('<li/>');
                        },
                        end: function() {
                            lis = ul.children('li');
                            lis.eachAsync(addLinks);
                        }
                    });
                }
            });
        });
    }

    /* User View */
    $('body.user a.accept, body.user a.deny').click(function() {
        return confirm(CONFIRM_MSG);
    });
    var profileDialogButtons = {};
    if ($("body").hasClass('user')) {
        profileDialogButtons[SAVE_MSG] = function() {
            $(this).find('form').submit();
        }
        profileDialogButtons[CANCEL_MSG] = function() {
            $(this).dialog('close');
        }
    }
    /*var profileDialog = $('body.user #profile-dialog').dialog({
        modal: true,
        autoOpen: false,
        buttons: profileDialogButtons,
        width: 500
    });  Dosen't work any more*/
    $('body.user .show-profile-dialog').click(function() {
        profileDialog.dialog('open');
    });


});
