/*
 * Simple test program for BGP-gRPC
 * Place in proto/bgp/test_bgp_grpc.c
 */

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <arpa/inet.h>

/* Mock BIRD types for standalone testing */
#ifndef BIRD_BUILD
typedef struct { int dummy; } rte;
typedef struct { int dummy; } rta; 
typedef struct { int dummy; } pool;
typedef struct { int dummy; } bgp_proto;
#else
#include "nest/bird.h"
#include "nest/route.h"
#include "bgp.h"
#endif

#include "bgp_grpc.h"

void test_state_callback(bgp_grpc_conn_t *conn, bgp_grpc_state_t old_state, bgp_grpc_state_t new_state) {
    printf("Test: State changed from %d to %d\n", old_state, new_state);
}

int main() {
    printf("BGP-gRPC Test Program\n");
    printf("====================\n");
    
    /* Initialize */
    if (bgp_grpc_init() != 0) {
        printf("Failed to initialize BGP-gRPC\n");
        return 1;
    }
    
    /* Create connection config */
    bgp_grpc_config_t config = {
        .remote_ip = "127.0.0.1",
        .remote_port = 41414,
        .local_as = 65001,
        .remote_as = 65002,
        .router_id = htonl(0x01010101), /* 1.1.1.1 */
        .state_callback = test_state_callback,
        .route_callback = NULL,
        .keepalive_time = 30,
        .hold_time = 90,
        .passive = false
    };
    
    /* Connect */
    printf("\nConnecting to %s:%d...\n", config.remote_ip, config.remote_port);
    bgp_grpc_conn_t *conn = bgp_grpc_connect(&config);
    if (!conn) {
        printf("Failed to create connection\n");
        bgp_grpc_cleanup();
        return 1;
    }
    
    /* Wait for connection */
    printf("Waiting for connection...\n");
    sleep(2);
    
    /* Check state */
    bgp_grpc_state_t state = bgp_grpc_get_state(conn);
    printf("Connection state: %d\n", state);
    
    if (state == BGP_GRPC_CONNECTED) {
        /* Test sending routes */
        printf("\nTesting route updates...\n");
        
        bgp_grpc_route_t route = {
            .prefix_ip = htonl(0xC0A80100), /* 192.168.1.0 */
            .prefix_len = 24,
            .next_hop_ip = htonl(0xC0A80001), /* 192.168.1.1 */
            .as_path = {65001, 65002},
            .as_path_len = 2,
            .origin = 0, /* IGP */
            .local_pref = 100
        };
        strcpy(route.update_type, "UPDATE");
        
        if (bgp_grpc_send_update(conn, &route) == 0) {
            printf("Route update sent successfully\n");
        } else {
            printf("Failed to send route update: %s\n", bgp_grpc_get_error(conn));
        }
        
        /* Test withdrawal */
        printf("\nTesting route withdrawal...\n");
        if (bgp_grpc_send_withdrawal(conn, htonl(0xC0A80100), 24) == 0) {
            printf("Route withdrawal sent successfully\n");
        } else {
            printf("Failed to send withdrawal: %s\n", bgp_grpc_get_error(conn));
        }
    }
    
    /* Process events */
    printf("\nProcessing events...\n");
    for (int i = 0; i < 5; i++) {
        bgp_grpc_process_events(conn);
        sleep(1);
    }
    
    /* Disconnect */
    printf("\nDisconnecting...\n");
    bgp_grpc_disconnect(conn);
    
    /* Cleanup */
    bgp_grpc_cleanup();
    
    printf("Test completed successfully!\n");
    return 0;
}
