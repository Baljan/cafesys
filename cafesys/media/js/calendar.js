/**
 * Tooltips
 */
var enableCalendarTooltips = function() {
    $(".day.has-shift.has-workers .day-of-month").tooltip({
        position: "top center",
        effect: 'slide',
    }).dynamic({});
};
var disableCalendarTooltips = function() {
    // FIXME: This is not working. The tooltips can be annoying when in add or
    // remove shifts mode.
    $(".day.has-shift .tooltip").hide();
};

/**
 * Utils.
 */
function getSchedId(obj) {
    return $(obj).attr('class').split(' ').slice(-1)[0];
}
function getLastClass(obj) {
    return $(obj).attr('class').split(' ').slice(-1)[0];
}

/**
 * Dajaxice callbacks.
 */
function processWorkerDialog(data) {
    Dajax.process(data);
    $('#worker-day-dialog').dialog({
        modal: true,
    });
    $('#worker-day-dialog .sign-up').click(function() {
        var shift = '';
        if ($(this).hasClass('morning')) shift = 'morning';
        else if ($(this).hasClass('afternoon')) shift = 'afternoon';
        var day = $(this).attr('class').split(' ').slice(-1)[0];
        Dajaxice.cal.sign_up('Dajax.process', { 
            id:'#worker-day-dialog', 
            redir_url: document.location.pathname,
            day: day, 
            shift: shift,
        });
    });
}

function processSendSwapRequestDialog(data) {
    Dajax.process(data);
    var send = function() {
        Dajaxice.cal.send_swap_request('Dajax.process', { 
            scheduled_id: getSchedId('#send-swap-request-dialog .sched-id'),
            offers: $.map($('#send-swap-request-dialog .selected span'), function(x) { return getSchedId(x); }),
            redir_url: document.location.pathname,
        });
    }
    $('#send-swap-request-dialog').dialog({
        modal: true,
        buttons: {
            // FIXME: Fetch a proper translation. "OK" just happens to work everywhere.
            'OK': send,
        },
    });
    $('#send-swap-request-dialog').unselectable();
    $('#send-swap-request-dialog ul li').click(function() {
        $(this).toggleClass('selected');
    });
}

function processRespondReceivedRequestDialog(data) {
    Dajax.process(data);
    var send = function() {
        Dajaxice.cal.respond_received_request('Dajax.process', { 
            swap_id: getSchedId('#respond-received-request-dialog .swap-id'),
            offer_id: getLastClass($('#respond-received-request-dialog .selected span')),
            redir_url: document.location.pathname,
        });
    }
    $('#respond-received-request-dialog').dialog({
        modal: true,
        buttons: {
            // FIXME: Fetch a proper translation. "OK" just happens to work everywhere.
            'OK': send,
        },
    });
    $('#respond-received-request-dialog').unselectable();
    $('#respond-received-request-dialog ul li').click(function() {
        $(this).siblings().removeClass('selected');
        $(this).toggleClass('selected');
    });
}


$(document).ready(function () {
    $('.calendars table', '.calendars h2').unselectable();
    $('#calendar-tasks', '#calendar-modes').unselectable();

    enableCalendarTooltips();

    $('.calendars').selectable({
        filter: 'td.in-month.shiftable',
        disabled: true,
        stop: function(ev, ui) {
            if ($('.ui-selected').size() == 0) {
                $('#calendar-tasks').hide();
                $('#calendar-tasks li').removeClass('selected');
                $('#calendar-tasks .confirmation').css('visibility', 'hidden');
            }
            else {
                $('#calendar-tasks').show();
            }
        },
    });

    var enableWorkerMode = function() {
        $('.calendars td.has-shift:not(.worker-count-4)').addClass('clickable').click(function() {
            $('#worker-day-dialog').remove();
            var day = $(this).attr('id');
            $('body').append([
                '<div style="display:none" id="worker-day-dialog" title="',day,'">',
                '<strong class="morning-title"></strong>',
                '<div class="body morning-body"></div>',
                '<strong class="afternoon-title"></strong>',
                '<div class="body afternoon-body"></div>',
                '<div class="extra"></div>',
                '</div>',
            ].join(''));
            Dajaxice.cal.worker_day_dialog('processWorkerDialog', {
                'id': '#worker-day-dialog',
                'day': day,
            });

        });
    }

    if (IS_BOARD_MEMBER) {
        $('#calendar-modes li').click(function() {
            $('#calendar-tasks').hide();
            $('.calendars .ui-selected').removeClass('ui-selected');

            $(this).siblings().removeClass('selected');
            $(this).toggleClass('selected');

            $('.calendars').selectable("disable");
            $('.calendars').removeClass("ui-state-disabled");
            $('.calendars td.has-shift:not(.worker-count-4)').removeClass('clickable').unbind('click');
            $('#worker-day-dialog').remove();

            if ($(this).hasClass('selected')) {
                if ($(this).hasClass('manage-shifts-mode')) {
                    $('.calendars').selectable("enable");
                }
                else if ($(this).hasClass('worker-mode')) {
                    enableWorkerMode();
                }
            }
        });

        $('#calendar-tasks .confirmation').click(function() {
            Dajaxice.cal.with_days('Dajax.process', {
                'url': document.location.pathname,
                'task': $('#calendar-tasks li.selected').attr('id'),
                'days': $.map($('.calendars .ui-selected'), function(x) { return x.id; }),
            });
        });

        $('#calendar-tasks li').click(function() {
            $(this).siblings().removeClass('selected');
            $(this).toggleClass('selected');

            if ($(this).parent().children().hasClass('selected')) {
                $('#calendar-tasks .confirmation').css('visibility', 'visible');
            }
            else {
                $('#calendar-tasks .confirmation').css('visibility', 'hidden');
            }
        });
    }
    else if (IS_WORKER) {
        enableWorkerMode();
    }


    $('.student-shifts .toggle-swappable').click(function() {
        Dajaxice.cal.toggle_swappable('Dajax.process', { 
            scheduled_id: getSchedId(this),
            redir_url: document.location.pathname,
        });
    });
    $('.student-shifts .remove-scheduled').click(function() {
        Dajaxice.cal.remove_from_scheduled('Dajax.process', { 
            scheduled_id: getSchedId(this),
            redir_url: document.location.pathname,
        });
    });

    $('.swappables .request-swap').click(function() {
        $('#send-swap-request-dialog').remove();
        $('body').append([
            '<div style="display:none" class="',getSchedId(this),'" id="send-swap-request-dialog">',
                '<strong class="offers-title"></strong>',
                '<div class="offers-body"></div>',
                '<div class="extra"></div>',
            '</div>',
        ].join(''));
        Dajaxice.cal.send_swap_request_dialog('processSendSwapRequestDialog', {
            'id': '#send-swap-request-dialog',
            'scheduled_id': getSchedId(this),
        });
    });

    $('.swap-requests .remove-sent-request').click(function() {
        Dajaxice.cal.remove_swap_request('Dajax.process', {
            swap_id: getLastClass(this),
            redir_url: document.location.pathname,
        });
    });

    $('.swap-requests .respond-received-request').click(function() {
        $('#respond-received-request-dialog').remove();
        $('body').append([
            '<div style="display:none" class="',getLastClass(this),'" id="respond-received-request-dialog">',
                '<div class="body"></div>',
                '<div class="extra"></div>',
            '</div>',
        ].join(''));
        Dajaxice.cal.respond_received_request_dialog('processRespondReceivedRequestDialog', {
            id: '#respond-received-request-dialog',
            swap_id: getLastClass(this),
        });
    });
});
