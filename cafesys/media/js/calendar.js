$(document).ready(function () {
    $('.calendars table', '.calendars h2').unselectable();
    $('#calendar-tasks').unselectable();

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
    });

    $('#manage-shifts-mode').click(function() {
        $(this).toggleClass('selected');

        if ($(this).hasClass('selected')) {
            $('.calendars').selectable("enable");
        }
        else {
            $('.calendars').selectable("disable");
            $('.calendars').removeClass("ui-state-disabled");
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

    $(".day.has-shift .day-of-month").tooltip({
        position: "top center",
        effect: 'slide',
    }).dynamic({
    });
});
