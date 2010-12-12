#include <ctype.h>
#include <stdio.h>
#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/io.h>

#include "parapin.h"

#define LPT_PCI 0xe400

#define PIN_MIN 2
#define PIN_MAX 7
#define OUT_OF_RANGE "pin out of range\n"

void show_help(char* exec)
{
    fprintf(stderr, "Usage: %s [-c] [-s PIN] [-u PIN] [-z MS]\n" \
        "    -c       unset all pins\n" \
        "    -s PIN   set pin high\n" \
        "    -u PIN   set pin low\n" \
        "    -z MS    sleep (milliseconds)\n" \
        "\n" \
        "Options can occur multiple times. Example:\n" \
        "\n" \
        "    %s -c -z 50 -s 3 -z 100 -u 3 -z 50 -c\n",
        exec, exec
    );
}

int main(int argc, char *argv[]){
    if (pin_init_user(LPT_PCI) < 0) {
        return -1;
    }
    pin_output_mode(LP_DATA_PINS | LP_SWITCHABLE_PINS);

    if (argc == 1) {
        show_help(argv[0]);
        return -1;
    }

    int c = 0;
    int i = -1;
    long int to_set_pin = -1;
    long int to_unset_pin = -1;
    long int sleep = -1;
    char *port_conv_end = NULL;

    while ((c = getopt(argc, argv, "hcs:u:z:")) != -1) {
        switch (c) {
            case 'h':
                show_help(argv[0]);
                break;
            case 'c':
                fprintf(stderr, "unset all\n");
                for (i = PIN_MIN; i <= PIN_MAX; ++i) {
                    clear_pin(LP_PIN[i]);
                }
                break;
            case 's':
                to_set_pin = strtol(optarg, &port_conv_end, 10);
                if (PIN_MIN <= to_set_pin && to_set_pin <= PIN_MAX) {
                    fprintf(stderr, "set pin %ld\n", to_set_pin);
                    set_pin(LP_PIN[to_set_pin]);
                }
                else {
                    fprintf(stderr, OUT_OF_RANGE);
                    return -1;
                }
                break;
            case 'u':
                to_unset_pin = strtol(optarg, &port_conv_end, 10);
                if (PIN_MIN <= to_unset_pin && to_unset_pin <= PIN_MAX) {
                    fprintf(stdout, "unset pin %ld\n", to_unset_pin);
                    clear_pin(LP_PIN[to_unset_pin]);
                }
                else {
                    fprintf(stderr, OUT_OF_RANGE);
                    return -1;
                }
                break;
            case 'z':
                sleep = strtol(optarg, &port_conv_end, 10);
                if (0 < sleep) {
                    fprintf(stderr, "sleeping for %ldms\n", sleep);
                    sleep = sleep * 1000; /* to milliseconds */
                    usleep(sleep);
                }
                else {
                    fprintf(stderr, "invalid sleep value");
                    return -1;
                }
                break;
            default:
                show_help(argv[0]);
                return -1;
        }
    }

    return 0;
}
