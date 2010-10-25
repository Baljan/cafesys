$(document).ready(function () {
    $('.init-hidden').css('visibility', 'visible').show();
    $('#links-for .accordion').accordion();
    $('#links-for').css('visibility', 'visible');
    $('#nav .active').click();

    $('input.dateinput').datepicker({ // TODO: i18n
        dateFormat:"yy-mm-dd",
        changeMonth: true,
        changeYear: true
    });

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

    /* Work Planning View */
    $('body.semester .tabs').tabs();

    var updateShifts = function() {
        var sem = $('.sem :selected:first').html(),
            upcomingOnly = $('#upcoming-only').attr('checked'),
            needWorkers = $('#need-workers').attr('checked'),
            needCallDuty = $('#need-call-duty').attr('checked'),
            onlySwitchable = $('#only-tradable').attr('checked'),
            filters = [],
            rows = '.tabs table tbody tr';

        if (needWorkers || needCallDuty || onlySwitchable) {
            $("#schedule table").addClass('plain');
            $('#upcoming-only').attr('checked', true).attr('disabled', true);
            upcomingOnly = true;
        }
        else {
            if ($(this).hasClass('past')) {
                // keep disabled
            }
            else {
                $('#upcoming-only').attr('disabled', false);
                $("#schedule table").removeClass('plain');
            }
        }

        if (upcomingOnly) {
            filters.push(function(row) {
                return $(row).hasClass('upcoming');
            });
        }
        if (needWorkers) {
            filters.push(function(row) {
                return $(row).find('.workers').hasClass('accepts');
            });
        }
        if (needCallDuty) {
            filters.push(function(row) {
                return $(row).find('.on-call').hasClass('accepts');
            });
        }
        if (onlySwitchable) {
            filters.push(function(row) {
                return $(row).find('.tradable').length != 0;
            });
        }

        $(rows).hide().filter(function() {
            for (i in filters) {
                if (filters[i](this) == false) {
                    return false;
                }
            }
            return true;
        }).show();
    }

    if ($('body').hasClass('semester')) {
        $('.filter').change(updateShifts).trigger('change');
    }
    
    /* Day View */
    // Disable sign-up if there are no user options to choose from.
    $('body.day form').each(function() {
        if ($(this).find('select[name=user] option').length == 0) {
            $(this).find('select[name=user]').hide();
            $(this).find('input[type=submit]').attr('disabled', true);
        }
    });
    $('body.day .worker input[type=submit]').click(function() {
        return confirm(CONFIRM_SIGNUP);
    });
    $('body.day .delete').click(function() {
        return confirm(CONFIRM_DELETE);
    });

    /* Search Person View */
    if ($('body').hasClass('search-person')) {
        var uFormat = function(user) {
            var uName = user.fields.username,
                fName = user.fields.first_name,
                lName = user.fields.last_name;
            return [fName,' ',lName,' (', uName, ')'].join('');
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
                    for (i in hits) {
                        ul.append('<li>' + uLink(hits[i]) + '</li>');
                        ul.find('li a').last().text(uFormat(hits[i]));
                    }
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
    var profileDialog = $('body.user #profile-dialog').dialog({
        modal: true,
        autoOpen: false,
        buttons: profileDialogButtons,
        width: 400
    });
    $('body.user .show-profile-dialog').click(function() {
        profileDialog.dialog('open');
    });
});
