function processOrdersPerDayAndHour(data)
{
    // FIXME: This function should be de-uglified. xs, axisx, ys, and axisy can
    // be fetched via AJAX. The day labels should use i18n (easiest via AJAX,
    // too).
    var xs = [ 
            8, 9,10,11,12,13,14,15,16,
            8, 9,10,11,12,13,14,15,16,
            8, 9,10,11,12,13,14,15,16,
            8, 9,10,11,12,13,14,15,16,
            8, 9,10,11,12,13,14,15,16],
        ys = [ 
            5, 5, 5, 5, 5, 5, 5, 5, 5,
            4, 4, 4, 4, 4, 4, 4, 4, 4,
            3, 3, 3, 3, 3, 3, 3, 3, 3,
            2, 2, 2, 2, 2, 2, 2, 2, 2,
            1, 1, 1, 1, 1, 1, 1, 1, 1],
        axisy = [ "Fri", "Thu", "Wed", "Tue", "Mon" ],
        axisx = ["8:00-", "9:00-", "10:00-", "11:00-", "12:00-", "13:00-", "14:00-", "15:00-", "16:00-16:59"];
        
        var r = Raphael("punch-card");
        r.g.txtattr.font = "11px arial, sans-serif";
        r.g.dotchart(10, 10, 620, 260, xs, ys, data.flat, {symbol: "o", max: data.maxval, heat:true, axis:"0 0 1 1", axisxstep: 8, axisystep: 4, axisxlabels: axisx, axisxtype: " ", axisytype:" ", axisylabels: axisy}).hover(function() {
            this.tag = this.tag || r.g.tag(this.x, this.y, this.value, 0, this.r + 2).insertBefore(this);
            this.tag.show();
            }, function () {
            this.tag && this.tag.hide();
        }); 
}

$(document).ready(function () {
    var autoUpdateInterval = 5 * 1000;

    var doUpdate = function() {
        Dajaxice.stats.orders_per_day_and_hour('processOrdersPerDayAndHour', {
        });
    }

    // Handle when the auto-update checkbox is clicked. This function
    // is for triggering an update immediately when the checkbox is
    // checked. The same for the "Update now" button.
    $('#auto-update').click(function() {
        if ($(this).attr('checked')) {
            doUpdate();
        }
    });
    $('#update-now').click(function() {
        doUpdate();
    });

    doUpdate(); // initial update when the page is first loaded

    // Automatic updater. This function will check the value of the checkbox
    // every time.
    $(document).everyTime(autoUpdateInterval, 'autoUpdate', function() {
        var autoUpdate = $('#auto-update').attr('checked');
        if (autoUpdate) {
            doUpdate();
        }
    });

    $('.date').datepicker({
        dateFormat:"yy-mm-dd",
        changeMonth: true,
        changeYear: true
        }); // TODO: i18n
});
