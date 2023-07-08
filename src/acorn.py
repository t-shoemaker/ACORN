#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
from numpy.linalg import inv

class LeakResistors:
    """A leak resistor matrix.

    Each document and term in the data has a corresponding resistor. We build a
    (num_doc + num_term)-length array and diagonalize it to a matrix, which
    will then be applied to a connection block.

    Example leak resistor matrix:

        [[0.1, 0.0, ..., 0.0],
         [0.0, 0.1, ..., 0.0],
         [0.0, 0.0, ..., 0.0],
         [0.0, 0.0, ..., 0.1]]

    This is the Λ block in equation 9 of Giuliano (1963).
    """
    def __init__(self, size: int, norm_by: float=1.) -> None:
        """Construct the matrix.

        Parameters
        ----------
        size
            Length of the diagnoal
        norm_by
            Normalization (0, 1) on the resistors
        """
        if not 0 <= norm_by <= 1.:
            raise ValueError("Normalization must be between 0 and 1.")

        self.size = size
        self.values = np.diag(np.repeat(norm_by, size))
        self.values = self.values.astype('float32')

    def __repr__(self) -> None:
        """Block repr."""
        return f"A ({self.size} x {self.size}) resistor matrix."

class Block:
    """A connection block, which represents electrical conductances in a
    circuit.

    This is the primary data structure in ACORN. It combines four different
    matrices: a document-term matrix (C), its transpose (B), a
    document-document matrix (E), and a term-term matrix (D). All matrices are
    normalized to unity (i.e. they are scaled from 0-1).

    When composed, the full Block looks like this:

        [[E, C],
         [B, D]]

    A Block is square matrix. Its dimensions are:
    
        (num_doc + num_term) x (num_doc + num_term)

    See the .compose() and .decompose() methods for information about how a
    Block's matrices are put together and broken apart when querying ACORN for
    document and word associations.
    """
    def __init__(self, DTM: np.matrix, norm_by: float=1.) -> None:
        """Construct the Block from a document-term matrix.

        Three additional matrices are constructed when a Block is initialized:

        B: Transpose of the document-term matrix
        E: A document-document matrix
        D: A term-term matrix

        Parameters
        ----------
        DTM
            The document-term matrix
        norm_by
            Normalization (0, 1) for the values
        """
        # Build the matrices
        self.num_doc, self.num_term = DTM.shape
        self.C = DTM.copy().astype('float32')
        self.B = self.C.T
        self.E = self.C @ self.B
        self.D = self.B @ self.C
        
        # Normalize all matrices to unity
        self.C = self.C / np.max(self.C)
        self.B = self.B / np.max(self.B)
        self.E = self.E / np.max(self.E)
        self.D = self.D / np.max(self.D)

        # Build identity matrices sized to document and term counts. We use
        # these to compute associations
        self.Idoc = np.identity(self.num_doc, dtype='float32')
        self.Iterm = np.identity(self.num_term, dtype='float32')

        # Set the normalization value and create an empty matrix for the Block
        self.norm_by = norm_by
        self.block_size = self.num_doc + self.num_term
        self.G = np.zeros((self.block_size, self.block_size), dtype='float32')

        # Compose the block
        self.compose()

    def __repr__(self) -> None:
        """Block repr."""
        return f"A ({self.block_size} x {self.block_size}) connection block."

    def compose(self, **kwargs) -> None:
        """Compose the Block.

        This gathers together the E, C, B, and D matrices and arranges them in
        a big matrix. It then applies normalization from the leak resistor
        matrix.

        The Block should be composed whenever we want to access some
        information about its connections. This is because the leak resistor
        normalization values can change from query to query. Likewise, some
        queries require adjustments to the component matrices of the Block. If
        the Block is composed without any arguments, it will pull from the
        original matrices as well as the original normalization value.
        Re-compose the Block at the end of a query or other operation to return
        the Block to its initializing state.

        Composing the Block is equation 1 in Giuliano (1963). Applying
        normalization to the Block is the second part of equation 9.

        Parameters
        ----------
        kwargs
            Optionally include the E, C, B, or D matrices as well as a new
            value for `norm_by`
        """
        E, C = kwargs.get('E', self.E), kwargs.get('C', self.C)
        B, D = kwargs.get('B', self.B), kwargs.get('D', self.D)
        block = np.block([[E, C], [B, D]])

        norm_by = kwargs.get('norm_by', self.norm_by)
        Λ = LeakResistors(self.block_size, norm_by)

        self.G = Λ.values @ block

    def decompose(self) -> tuple[np.matrix]:
        """Decompose the Block into its constituent parts.

        Run a Block decomposition whenver you want to access the component
        matrices after they've been modified in some way by normalization or
        other value updates.

        Returns
        -------
        E, C, B, D
            Separated parts of the Block
        """
        E = self.G[:self.num_doc, :self.num_doc]
        C = self.G[:self.num_doc, self.num_doc:]
        B = self.G[self.num_doc:, :self.num_doc]
        D = self.G[self.num_doc:, self.num_doc:]

        return E, C, B, D

    def query(self, Q: np.ndarray, norm_by: float=1.) -> np.matrix:
        """Find document assocations for a query.

        A query is a num_term-length array of 0s and 1s. 1 means a term has
        been selected, while 0 is a deselected term.

        This is equation 12 in Giuliano (1963).

        Parameters
        ----------
        Q
            The query vector
        norm_by
            Normalization (0, 1) values for the Block
        
        Returns
        -------
        A
            Document association values for the query
        """
        # Validate the query and compose the Block with our `norm_by` value
        if len(Q) > self.num_term:
            raise ValueError("Query length cannot exceed number of terms.")

        if np.isclose(self.norm_by, norm_by):
            norm_by = self.norm_by

        self.compose(norm_by=norm_by)

        # Decompose the Block and build the components of the equation
        E, C, B, D = self.decompose()
        facA = inv(self.Idoc - E) @ (C @ inv(self.Iterm - D))
        facB = inv(
            self.Iterm - (B @ inv(self.Idoc - E)) @ (C @ inv(self.Iterm - D))
        )

        # Re-compose the Block from the initializing data
        self.compose()

        return facA @ facB @ Q

    def query_DTM(self, Q: np.ndarray, norm_by: float=1.) -> np.matrix:
        """Query document associations assuming no information about term-term
        or document-document interaciton is available.

        This is equation 13 in Giuliano (1963).

        Parameters
        ----------
        Q
            The query vector
        norm_by
            Normalization (0, 1) values for the Block

        Returns
        -------
        A
            Document association values for the query
        """
        # Since we're discounting any information we'd otherwise gain from the
        # document-document and term-term matrices, we zero these out
        E0 = np.zeros((self.num_doc, self.num_doc))
        D0 = np.zeros((self.num_term, self.num_term))

        # Compose the Block with these zeroed matrices, then decompose it.
        # Build the components of the equation after that
        self.compose(E=E0, D=D0, norm_by=norm_by)
        E, C, B, D = self.decompose()

        facA = C @ inv(self.Iterm - (B @ C))

        # Re-compose the Block from the initializing data
        self.compose()

        return facA @ Q

    def word_associations(self) -> np.matrix:
        """Find word-word associations in a Block.

        This is discussed after equation 12 in Giuliano (1963, 230).

        Returns
        -------
        associations
            Word associations
        """
        # Decompose the Block and build the components of the equation
        E, C, B, D = self.decompose()
        facA = inv(self.Iterm - D)
        facB = inv(
            self.Iterm - ((B @ inv(self.Idoc - E)) @ (C @ inv(self.Iterm - D)))
        )

        return facA @ facB

    def document_associations(self) -> np.matrix:
        """Find document-document associations in a Block.

        This is discussed after equation 12 in Giuliano (1963, 230).

        Returns
        -------
        associations
            Document associations
        """
        # Decompose the Block and retrieve the document-document matrix
        E, *_ = self.decompose()
        
        return inv(self.Idoc - E)
