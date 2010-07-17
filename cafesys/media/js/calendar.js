/**
 * Tooltips
 */
var enableCalendarTooltips = function() {
    $(".day.has-shift .day-of-month").tooltip({
        position: "top center",
        effect: 'slide',
    }).dynamic({});
}
var disableCalendarTooltips = function() {
    // FIXME: This is not working. The tooltips can be annoying when in add or
    // remove shifts mode.
    $(".day.has-shift .tooltip").hide();
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
        }
    });

    $('#calendar-tasks .confirmation').click(function() {
        $('body').css('cursor', 'wait');
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

});
