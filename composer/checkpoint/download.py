# Copyright 2024 MosaicML Composer authors
# SPDX-License-Identifier: Apache-2.0

"""Useful functions for load checkpoints from remote object store or local disk."""
import logging

from composer.utils import (
    dist,
    maybe_create_object_store_from_uri,
    parse_uri,
    extract_path_from_symlink,
    retry,
)

log = logging.getLogger(__name__)

def download_file(
    source_uri: str, 
    destination_path: str, 
    node_ranks: Optional[List[int]]=None, 
    num_attempts=5,
):
    """
    Downloads a file (object) from the specified URI to the specified directory.

    Args:
        source_uri (str): The URI to download the file from or a symlink to the URI.
        destination_path (str): The directory to download the file to.
        node_ranks (List[int]): The ranks of the nodes that will download the file. If None, all nodes will download the file.
    """
    # Only local rank 0 downloads
    local_rank = dist.get_local_rank()
    if local_rank != 0:
        return

    node_rank = dist.get_node_rank()
    if node_ranks is not None and node_rank not in node_ranks:
        return

    object_store = maybe_create_object_store_from_uri(load_path)
    _, _, source_path = parse_uri(source_uri)
    if source_uri.endswith('.symlink'):
        source_path = extract_path_from_symlink(source_path, object_store)
    
    @retry(num_attempts=num_attempts)
    def _download():
        object_store.download_object(
            object_name=source_path,
            filename=destination_path,
        )

    log.debug(f'Downloading {source_path} to {destination_path}')
    _download()
    log.debug(f'Finished downloading {source_path} to {destination_path}')


def download_monolithic_checkpoint(
    source_uri: str,
    destination_path: str,
):
    pass
    
def download_sharded_checkpoint(
    src_dir_uri: str,
    dest_path: str,
    metadata_path: str,
    #broadcast_files_to_other_nodes: bool = False,
    replica_pg: # HSDP usecase
):
    pass



def _download_monolithic_checkpoint(
    source_uri: str,
    destination_path: str,
    rank_zero_only: bool = True,
    broadcast_file_to_other_nodes: bool = False,
):
    """"
    Downloads a monolithic checkpoint from the specified URI to the specified directory.


    Args:
        source_uri (str): The URI to download the checkpoint from or symlink that points to the URI.
        destination_path (str): The directory to download the checkpoint to.
        rank_zero_only (bool): If True, only rank 0 will download the checkpoint.
        broadcast_files_to_other_nodes (bool): If True, the downloaded checkpoint will be broadcast to all other nodes. 
            If torch syncs modules states this is unnecessary.
    Returns:
        str: The full path to the downloaded checkpoint.
    """
    node_ranks = None
    if rank_zero_only:
        node_ranks = [0]
    download_file(
        source_uri=source_uri,
        destination_path=dest_path,
        node_ranks=node_ranks,
    )
    if not broadcast_file_to_other_nodes:
        global_rank = dist.get_global_rank()
        if rank_zero_only and global_rank != 0:
            return None
        return destination_path
    
    if not rank_zero_only:
        return destination_path

    # Need broadcast

