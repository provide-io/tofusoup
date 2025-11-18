package main

import (
	"fmt"
	"strings"

	"github.com/hashicorp/go-plugin"
	"github.com/spf13/cobra"
)

// getCurve returns the elliptic curve for the given curve name
func initKVGetCmd() *cobra.Command {
	var address string
	var tlsCurve string

	cmd := &cobra.Command{
		Use:   "get [key]",
		Short: "Get a value from the RPC KV server",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			key := args[0]

			var client *plugin.Client
			var err error

			// Use reattach if --address is provided, otherwise spawn server
			if address != "" {
				client, err = newReattachClient(address, tlsCurve, logger)
				if err != nil {
					return err
				}
			} else {
				client, err = newRPCClient(logger)
				if err != nil {
					return err
				}
			}
			defer client.Kill()

			rpcClient, err := client.Client()
			if err != nil {
				return fmt.Errorf("failed to create RPC client: %w", err)
			}

			// Dispense the plugin to get our KV interface
			raw, err := rpcClient.Dispense("kv_grpc")
			if err != nil {
				return fmt.Errorf("failed to dispense plugin: %w", err)
			}
			kv := raw.(KV)

			value, err := kv.Get(key)
			if err != nil {
				return fmt.Errorf("failed to get key %s: %w", key, err)
			}

			fmt.Printf("%s\n", value)
			return nil
		},
	}

	cmd.Flags().StringVar(&address, "address", "", "Address of existing server (e.g., 127.0.0.1:50051)")
	cmd.Flags().StringVar(&tlsCurve, "tls-curve", "auto", "Client cert curve: auto (detect from server), secp256r1, secp384r1, secp521r1")
	return cmd
}

// Override the kvput command with real implementation
func initKVPutCmd() *cobra.Command {
	var address string
	var tlsCurve string

	cmd := &cobra.Command{
		Use:   "put [key] [value]",
		Short: "Put a key-value pair into the RPC KV server",
		Args:  cobra.ExactArgs(2),
		RunE: func(cmd *cobra.Command, args []string) error {
			key := args[0]
			value := []byte(args[1])

			var client *plugin.Client
			var err error

			// Use reattach if --address is provided, otherwise spawn server
			if address != "" {
				client, err = newReattachClient(address, tlsCurve, logger)
				if err != nil {
					return err
				}
			} else {
				client, err = newRPCClient(logger)
				if err != nil {
					return err
				}
			}
			defer client.Kill()

			rpcClient, err := client.Client()
			if err != nil {
				return fmt.Errorf("failed to create RPC client: %w", err)
			}

			// Dispense the plugin to get our KV interface
			raw, err := rpcClient.Dispense("kv_grpc")
			if err != nil {
				return fmt.Errorf("failed to dispense plugin: %w", err)
			}
			kv := raw.(KV)

			if err := kv.Put(key, value); err != nil {
				return fmt.Errorf("failed to put key %s: %w", key, err)
			}

			fmt.Printf("Key %s put successfully.\n", key)
			return nil
		},
	}

	cmd.Flags().StringVar(&address, "address", "", "Address of existing server (e.g., 127.0.0.1:50051)")
	cmd.Flags().StringVar(&tlsCurve, "tls-curve", "auto", "Client cert curve: auto (detect from server), secp256r1, secp384r1, secp521r1")
	return cmd
}

// Override the validateconnection command with real implementation
func initValidateConnectionCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "connection",
		Short: "Validate connection to the RPC KV server",
		Args:  cobra.NoArgs,
		RunE: func(cmd *cobra.Command, args []string) error {
			// This will attempt to connect and perform a simple operation
			// If it succeeds, the connection is valid.
			client, err := newRPCClient(logger)
			if err != nil {
				return err
			}
			defer client.Kill()

			raw, err := client.Client()
			if err != nil {
				return fmt.Errorf("failed to create RPC client: %w", err)
			}
			kv := raw.(KV)

			// Perform a simple Get on a non-existent key to validate connection
			_, err = kv.Get("__connection_test_key__")
			if err != nil && !strings.Contains(err.Error(), "key not found") {
				return fmt.Errorf("connection validation failed: %w", err)
			}

			fmt.Println("RPC connection validated successfully.")
			return nil
		},
	}
	return cmd
}

// newRPCClient creates a new go-plugin client for the KV service
