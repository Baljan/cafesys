$(document).ready(function () {
    $('.calendars').unselectable();
    $('#calendar-tasks').unselectable();
    $('.calendars').selectable({
        filter: 'td.in-month.shiftable',
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

    $(".day.has-shift .day-of-month").tooltip({
        position: "top center",
        effect: 'slide',
    }).dynamic({
    });
});
