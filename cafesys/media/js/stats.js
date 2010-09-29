function processOrdersPerDayAndHour(data)
{
    // FIXME: This function should be de-uglified.
    var xs = [ 
            8,9,10,11,12,13,14,15,16,17,
            8,9,10,11,12,13,14,15,16,17,
            8,9,10,11,12,13,14,15,16,17,
            8,9,10,11,12,13,14,15,16,17,
            8,9,10,11,12,13,14,15,16,17],
        ys = [ 
            5,5, 5, 5 ,5 ,5 ,5 ,5, 5, 5,
            4,4, 4, 4 ,4 ,4 ,4 ,4, 4, 4,
            3,3, 3, 3 ,3 ,3 ,3 ,3, 3, 3,
            2,2, 2, 2 ,2 ,2 ,2 ,2, 2, 2,
            1,1, 1, 1 ,1 ,1 ,1 ,1, 1, 1],
        axisy = [ // TODO: i18n
            "Fri", "Thu", "Wed", "Tue", "Mon" ],
        axisx = ["08", "09", "10", "11", "12", "13", 
                "14", "15", "16", "17"];
        
        var r = Raphael("punch-card");
        r.g.txtattr.font = "11px arial, sans-serif";
        r.g.dotchart(10, 10, 620, 260, xs, ys, data.flat, {symbol: "o", max: data.maxval, heat:true, axis:"0 0 1 1", axisxstep: 9, axisystep: 4, axisxlabels: axisx, axisxtype: " ", axisytype:" ", axisylabels: axisy}).hover(function() {
            this.tag = this.tag || r.g.tag(this.x, this.y, this.value, 0, this.r + 2).insertBefore(this);
            this.tag.show();
            }, function () {
            this.tag && this.tag.hide();
        }); 
}

$(document).ready(function () {
    Dajaxice.stats.orders_per_day_and_hour('processOrdersPerDayAndHour', {
    });
});
