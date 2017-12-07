$(document).ready(function () {
    $('.init-hidden').css('visibility', 'visible').show();
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
    var profileDialog = $('body.user #profile-dialog').dialog({
        modal: true,
        autoOpen: false,
        buttons: profileDialogButtons,
        width: 500
    });
    $('body.user .show-profile-dialog').click(function() {
        profileDialog.dialog('open');
    });

    /* Job Opening View */
    if ($("body").hasClass('job-opening')) {
        var slots = $('.slots td.pair.free'),
            takenSlots = $('.slots td.pair.taken'),
            curSearch = false,
            idInput = $('#id_liu_id'),
            msg = $('.user-adder .message span'),
            msgClasses = ['pending', 'saved', 'invalid'],
            addButton = $('#add-to-group'),
            foundUser = false,
            addedUsers = {},
            addedList = $('.work-pair'),
            currentComb = $('.shifts-in-combination'),
            currentCombLabel = false,
            currentCombShiftIds = [],
            saveForm = $('.submit-wrap form'),
            submitBox = $('.submit-wrap');

        var refreshSave = function() {
            var addedUsersCount = 0,
                submitButton = submitBox.find('input[type=submit]');

            for (k in addedUsers) {
                addedUsersCount += 1;
            }
            if (currentCombShiftIds.length == 0 ||
                addedUsersCount != 2) {
                saveForm.find('input[name=shift-ids]').attr('value', '');
                saveForm.find('input[name=user-ids]').attr('value', '');
                saveForm.find('input[name=phones]').attr('value', '');

                submitBox.removeClass('saved');
                submitBox.addClass('pending');
                submitButton.attr('disabled', 'disabled');
                submitButton.attr('value', SUBMIT_HELP);
            }
            else {
                var serialShiftIds = currentCombShiftIds.join('|'),
                    serialUsernames = [],
                    serialPhones = [];

                for (i in addedUsers) {
                    serialUsernames.push(i);
                    serialPhones.push($('.phone-' + i).attr('value'));
                }
                serialUsernames = serialUsernames.join('|');
                serialPhones = serialPhones.join('|');

                saveForm.find('input[name=shift-ids]')
                        .attr('value', serialShiftIds);
                saveForm.find('input[name=user-ids]')
                        .attr('value', serialUsernames);
                saveForm.find('input[name=phones]')
                        .attr('value', serialPhones);

                submitBox.addClass('saved');
                submitBox.removeClass('pending');
                submitButton.removeAttr('disabled');
                submitButton.attr('value', SUBMIT_OK);
            }
        }
        refreshSave();

        var setActiveComb = function(cell) {
            slots.removeClass('active');
            currentCombLabel = $.trim($(cell).text());
            var pair = PAIRS[currentCombLabel];
            var shifts = pair.shifts;
            if ($(cell).hasClass('free')) {
                currentCombShiftIds = pair.ids;
                $(cell).toggleClass('active');
            }
            else {
                currentCombShiftIds = [];
            }
            currentComb.html('');
            for (i in shifts) {
                currentComb.append('<li/>');
                currentComb.find('li:last').text(shifts[i]);
            }
            refreshSave();
        }

        $('.combination-progress').progressbar({
            value: COMBINATION_PROGRESS
        });
        slots.unselectable();
        slots.click(function() {
            setActiveComb(this);
        });
        takenSlots.unselectable();
        takenSlots.click(function() {
            setActiveComb(this);
        });

        var addUser = function() {
            if (!foundUser) return;

            idInput.attr('value', '');
            refreshSearch();

            addedUsers[foundUser.username] = foundUser;
            refreshAdded();
        }

        var removeUser = function(id) {
            delete addedUsers[id];
            refreshAdded();
        }

        var refreshAdded = function() {
            addedList.find('li').remove();
            for (i in addedUsers) {
                var user = addedUsers[i];
                addedList.append('<li><a/></li>');
                var last = addedList.find('li:last');
                last.data('username', i);
                var link = last.find('a');
                link.attr('href', user.url);
                link.text(user.text);
                last.append(' <span class="remove link">&#x2715;</span>');
                last.append('<br/>'+PHONE_TEXT+' <input type="text" maxlength="10" style="width:50%"/>');
                var phone = last.find('input');
                $(phone).addClass('phone-' + i);
                $(phone).attr('value', user.phone);
                $(phone).data('username', i);
                $(phone).keyfilter(/[\d]/);
                $(phone).change(function() {
                    var uName =$(this).data('username');
                    addedUsers[uName].phone = $(this).attr('value');
                    refreshSave();
                });
            }

            addedList.find('li .remove').click(function() {
                removeUser($(this).parent().data('username'));
            });
            refreshSave();
        }

        var refreshSearch = function() {
            var term = idInput.attr('value');
            if (0 < term.length && term.length < 5) return;
            if (curSearch) curSearch.abort();

            curSearch = $.ajax({
                data: {'liu_id': term},
                type: 'post',
                dataType: 'json',
                success: function(result) {
                    if (!result) return;

                    for (i in msgClasses) {
                        if (result.msg_class == msgClasses[i])
                            msg.addClass(msgClasses[i]);
                        else msg.removeClass(msgClasses[i]);
                    }
                    msg.text(result.msg);
                    if (result.all_ok) {
                        addButton.removeAttr('disabled');
                        foundUser = result.user;
                        addButton.click();
                    }
                    else {
                        addButton.attr('disabled', 'disabled');
                        foundUser = false;
                    }
                }
            });
        }

        addButton.click(addUser);
        idInput.bind('keyup', refreshSearch);
    }


    /* Board Week Planning */
    if ($("body").hasClass('board-week')) {
        var availUsers = $('.available-users'),
            names = [];

        $('.chalkboard').unselectable();

        for (i in USER_IDS) {
            names.push(DRAGS[USER_IDS[i]]);
        }
        availUsers.html(names.join(', '));

        var redrawContained = function(cell) {
            var listed = [],
                containedInits = $(cell).data('initials');
            for (i in containedInits) {
                listed.push([
                    '<span class="drag-',containedInits[i],'">',
                    containedInits[i],'</span>'
                ].join(''));
            }
            $(cell).html(listed.join(', '));
            $(cell).children().each(function() {
                $(this).click(function() { 
                    var newContained = [];
                    for (j in containedInits) {
                        if (containedInits[j] != $(this).text()) {
                            newContained.push(containedInits[j]);
                        }
                        $(cell).data('initials', newContained);
                    }
                    $(this).trigger('mouseleave').remove();
                    redrawContained(cell);
                });
            });

            $(containedInits).each(function() {
                var cls = $('.drag-' + this),
                    id = $("#drag-" + this);
                cls.hover(
                    function() {
                        cls.addClass('active')
                           .parent().addClass('active');
                        id.addClass('active')
                    },
                    function() {
                        cls.removeClass('active')
                           .parent().removeClass('active');
                        id.removeClass('active')
                    }
                );
            });
        }
        
        /* Load initial data. */
        $('.droppable').each(function() {
            var id = $(this).attr('id');
            if (!REAL_IDS[id]) {
                $(this).addClass('disabled');
            }
            var onCallUids = ON_CALL[id],
                inits = [];
            for (i in onCallUids) {
                inits.push(INITIALS[onCallUids[i]]);
            }
            $(this).data('initials', inits);
            redrawContained(this);
        });

        $('.droppable').each(function() {
            var drop = this;
            $(this).droppable({
                accept: function(drag) {
                    if ($(this).hasClass('disabled')) return false;
                    return $(drop).find('.'+drag.attr('id')).length == 0;
                },
                activeClass: 'active',
                hoverClass: 'hover',
                drop: function(ev, ui) {
                    var dragId = $(ui.draggable).attr('id');
                    var droppedInit = dragId.split('-')[1],
                        containedInits = $(this).data('initials'),
                        cell = this;
                    if (!containedInits) containedInits = [droppedInit];
                    else containedInits.push(droppedInit);
                    $(this).data('initials', containedInits);
                    redrawContained(cell);
                }
            });
        });

        $('.available-users').children().each(function() {
            var initials = $(this).attr('id').split('-')[1]
                cls = 'drag-' + $(this).attr('id').split('-')[1],
                drag = this;

            $(this).draggable({
                cursorAt: {right: 3, bottom: 3},
                helper: function(ev) { 
                    var ui = $("<span class='drag "+cls+"'>"+initials+"</span>"); 
                    return ui;
                },
                opacity: 0.7
            });

            $(this).hover(function() {
                var ui = $('.'+$(this).attr('id'));
                ui.addClass('active')
                  .parent().addClass('active');
                $(this).addClass('active');
            }, function() {
                var ui = $('.'+$(this).attr('id'));
                ui.removeClass('active')
                  .parent().removeClass('active');
                $(this).removeClass('active');
            });
        });

        $('.submit .save').click(function() {
            var postData = {};
            $('.droppable').each(function() {
                var containedInits = $(this).data('initials');
                if (!containedInits || containedInits.length == 0) return;

                postData[$(this).attr('id')] = containedInits.join('|');
            });
            curSearch = $.ajax({
                data: postData,
                type: 'post',
                dataType: 'json',
                beforeSend: function () {
                    $('.submit .save').html("Sparar...");
                },
                success: function(result) {
                    location.replace(document.location.pathname);
                },
                error: function() {
                    location.replace(document.location.pathname);
                }
            });
        });
    }

    /* Semester Administration */
    if ($("body").hasClass('admin-semester')) {
        var editShiftsForm = $('form[name=edit-shifts]'),
            shiftInners = $('table td.shift div');

        $('table').unselectable();
        $('.months').selectable({
            filter: 'td.shift',
            stop: function(ev, ui) {
                var inputs = editShiftsForm.find('input[type=button]');
                if ($('table td.ui-selected').length) {
                    $(inputs).removeAttr('disabled');
                }
                else {
                    $(inputs).attr('disabled', 'disabled');
                }
            }
        });

        $(shiftInners).hover(function() {
            var comb = $(this).html();
            if (comb == '&nbsp;') return;
            $(shiftInners).filter(function() {
                return $(this).html() == comb;
            }).addClass('highlight');
        }, function() {
            var comb = $(this).html();
            if (comb == '&nbsp;') return;
            $(shiftInners).filter(function() {
                return $(this).html() == comb;
            }).removeClass('highlight');
        });

        $('input[name=start]').datepicker({ // TODO: i18n
            dateFormat:"yy-mm-dd",
            changeMonth: true,
            changeYear: true
        });
        $('input[name=end]').datepicker({ // TODO: i18n
            dateFormat:"yy-mm-dd",
            changeMonth: true,
            changeYear: true
        });

        var newSemDialogButtons = {};
        newSemDialogButtons[SAVE_MSG] = function() {
            $(this).find('form').submit();
        }
        newSemDialogButtons[CANCEL_MSG] = function() {
            $(this).dialog('close');
        }
        var newSemDialog = $('#new-sem-dialog').dialog({
            modal: true,
            autoOpen: false,
            buttons: newSemDialogButtons,
            width: 500
        });
        $('.show-new-sem-dialog').click(function() {
            newSemDialog.dialog('open');
        });
        if (NEW_SEMESTER_FAILED) {
            $('.show-new-sem-dialog').click();
        }
        $('.selection input').click(function() {
            editShiftsForm.find('input[name=make]').attr('value', $(this).attr('class'));
            var shiftIds = [];
            $('table td.ui-selected').each(function() {
                shiftIds.push(parseInt($(this).attr('id').split('-')[1], 10));
            });
            editShiftsForm.find('input[name=shift-ids]')
                          .attr('value', shiftIds.join('|'));

            if (confirm(CONFIRM_MSG)) {
                editShiftsForm.submit();
            }
        });

        $('.choose-semester select').change(function() {
            var name = $(this).children(':selected').html();
            location.href = '' + BASE_URL + '/' + name;
        });
    }

    /* Job Opening Projector View */
    if ($('body').hasClass('job-opening-projector')) {
        var curRequest = false,
            updateFreq = 5, // seconds
            lastUpdate = $('.last-updated span');

        $(document).everyTime(updateFreq * 1000, function(i) {
            if (curRequest) curRequest.abort();
            curRequest = $.ajax({
                url: document.location.pathname,
                dataType: 'json',
                success: function(data) {
                    $(data.pairs).each(function() {
                        var slot = $('#pair-' + this.label);
                        if (this.free) {
                            $(slot).removeClass('taken');
                            $(slot).fadeTo('slow', 1.0, function() {
                                $(slot).addClass('free');
                            });
                        }
                        else {
                            if ($(slot).hasClass('free')) {
                                $(slot).fadeTo('slow', 0.0, function() {
                                    $(slot).removeClass('free');
                                    $(slot).addClass('taken');
                                });
                            }
                        }
                        $(lastUpdate).html(data.now);
                    });
                }
            });
        });
    }
});
