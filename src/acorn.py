#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
from numpy.linalg import inv

class Block:
    """A base class circuit block, which represents electrical currents.

    This is the primary data structure in ACORN. It combines four different
    matrices: a document-term matrix (C), its transpose (B), a
    document-document matrix (E), and a term-term matrix (D).

    When composed, the full Block looks like this:

        [[E, C],
         [B, D]]

    A Block is a square matrix. Its dimensions are the sum of C's length and
    width.

    See the `.compose()` and `.decompose()` methods for information about how a
    Block's matrices are put together and broken apart when querying ACORN for
    document and word associations.
    """
    def __init__(self, data: np.ndarray) -> None:
        """Construct the Block.

        Parameters
        ----------
        data
            A two-dimensional array upon which to base the Block components
        """
        # Block metadata. The attributes `.m` and `.n` refer to the number of
        # documents and terms, respectively. The `.size` attribute is the full
        # length/width of the Block, and `.kind` is a flag for the repr
        self.m, self.n = data.shape
        self.size = self.m + self.n
        self.kind = "base"

        # Build the primary Block components. See the `.compose()` method
        self.C = data.copy().astype('float32')
        self.B = self.C.T
        self.E = self.C @ self.B
        self.D = self.B @ self.C

        # The full Block
        self.G = np.zeros((self.size, self.size), dtype='float32')

    def __repr__(self) -> str:
        """Block repr."""
        return f"A ({self.size} x {self.size}) {self.kind} block."

    @property
    def state(self) -> np.ndarray:
        """The current state of the Block."""
        return self.G

    def compose(self, **kwargs):
        """Compose the Block.

        This gathers together the E, C, B, and D matrices and arranges in them
        in a big matrix.

        Different query methods require certain alterations to the Block's
        components (e.g. normalization, zeroed-out portions of the Block). This
        method should be called by those queries to produce the appropriate
        components before associations are calculated. Similarly, child classes
        should compose the Block during construction if their `.__init__()`
        methods differ from the parent class. The parent class does not run a
        Block composition when initialized; instead, it creates a (size x size)
        matrix of 0s.

        If a Block is composed without any arguments, it will pull from its
        original matrices. Re-compose the Block at the end of a query or other
        operation to return the Block to its initializing state.

        Composing the Block is equation 1 in Giuliano (1963).

        Parameters
        ----------
        kwargs
            Optionally include the E, C, B, or D matrices
        """
        E, C = kwargs.get('E', self.E), kwargs.get('C', self.C)
        B, D = kwargs.get('B', self.B), kwargs.get('D', self.D)
        block = np.block([[E, C], [B, D]])

        self.G = block

    def decompose(self) -> tuple[np.ndarray]:
        """Decompose the Block into its constituent parts.

        Run a Block decomposition whenever you want to access the component
        matrices after they've been modified in some way by a query.

        Returns
        -------
        E, C, B, D
            Separated parts of the Block
        """
        E = self.G[:self.m, :self.m]
        C = self.G[:self.m, self.m:]
        B = self.G[self.m:, :self.m]
        D = self.G[self.m:, self.m:]

        return E, C, B, D

class ResistorBlock(Block):
    """A leak resistor Block.

    Each document and term in the data has a corresponding resistor; this Block
    builds a matrix that contains those values and affixes them to the
    appropriate locations in that matrix.

    Example ResistorBlock:

        [[0.1, 0.0, ..., 0.0],
         [0.0, 0.1, ..., 0.0],
         [0.0, 0.0, ..., 0.0],
         [0.0, 0.0, ..., 0.1]]

    This is the Λ matrix in equation 9 of Giuliano (1963).
    """
    def __init__(self, data: np.ndarray, norm_by: float=1.) -> None:
        """Construct the Block.
        
        Parameters
        ----------
        data
             A two-dimensional array upon which to base the ResistorBlock
             components
        norm_by
            Normalization (0, 1) on the resistors
        """
        # This matrix has everything zeroed-out except the diagonal
        data = np.zeros_like(data)

        # Run the Block's constructor
        super().__init__(data=data)
        self.kind = "resistor"
        
        # Fill the diagonal of E and D
        self.norm_by = norm_by
        np.fill_diagonal(self.E, self.norm_by)
        np.fill_diagonal(self.D, self.norm_by)

        # Run a composition because the components have changed
        self.compose()

class ConnectionBlock(Block):
    """A connection Block, which represents electrical conductances in a
    circuit.

    All queries are made with this class. Unlike the base Block class, a
    ConnectionBlock retains the values of its input data and exposes methods
    for making queries.

    When initialized, each component in a ConnectionBlock is normalized to
    unity (i.e. L2/Euclidean norm). A ConnectionBlock is further normalized by
    a ResistorBlock. This operation is implemented in the former's `.compose()`
    method; query methods may also change the normalization.
    """
    def __init__(self, DTM: np.ndarray, norm_by: float=1.) -> None:
        """Construct the Block.
        
        Parameters
        ----------
        DTM
            The document-term matrix (a two-dimensional array of value counts)
        norm_by
            Normalization (0, 1) to apply
        """
        # Run the Block's constructor
        super().__init__(data=DTM)
        self.kind = "connection"

        # Normalize the components
        self.C = self._norm(self.C)
        self.B = self._norm(self.B)
        self.E = self._norm(self.E)
        self.D = self._norm(self.D)

        # Build identity matrices sized to document and term counts. We use
        # these to compute associations
        self.Idoc = np.identity(self.m, dtype='float32')
        self.Iterm = np.identity(self.n, dtype='float32')

        # Set the normalization value and compose the ConnectionBlock
        self.norm_by = norm_by
        self.compose()

    def compose(self, **kwargs) -> None:
        """Compose the ConnectionBlock.

        In addition to gathering together the E, C, B, and D matrices, this
        method applies normalization from a ResistorBlock.

        Parameters
        ----------
        kwargs
            Optionally include the E, C, B, or D matrices as well as a
            normalization value (`norm_by`)
        """
        # Run a composition
        super().compose(**kwargs)

        # Get the normalization value. Then construct a ResistorBlock
        norm_by = kwargs.get('norm_by', self.norm_by)
        Λ = ResistorBlock(self.C, norm_by=norm_by)

        # Normalize with values from the ResistorBlock
        self.G = Λ.state @ self.G

    def _norm(self, data: np.array, axis: int=1) -> np.array:
        """Normalize data to unity.

        Parameters
        ----------
        data
            The data to norm
        axis
            Axis to apply the norm

        Returns
        -------
        normalized
            Normed data
        """
        l2 = np.linalg.norm(data, axis=1, keepdims=True)
        normalized = data / l2

        return normalized

    def _validate_query(self, Q: np.ndarray):
        """Validate a query.

        A valid query is one with a length of self.n slots, which contain
        either 0s or 1s.

        Parameters
        ----------
        Q
            The query vector

        Raises
        ------
        ValueError
            If the query length does not match the number of terms
        ValueError
            If the query contains numbers other than 0 or 1
        """
        if len(Q) != self.n:
            raise ValueError("Query length must equal the number of terms")

        if not np.all((Q == 0) | (Q == 1)):
            raise ValueError("Query must contain 0 or 1 for all slots")

    def _set_state(self, norm_by: float, **kwargs):
        """Set the state with a normalization value and optional matrices.

        Parameters
        ---------
        norm_by
            Normalization (0, 1) for the Block
        kwargs
            Any other arguments for Block composition
        """
        close = np.isclose(self.norm_by, norm_by)
        if not close and kwargs:
            self.compose(norm_by=norm_by, **kwargs)
        elif not close and not kwargs:
            self.compose(norm_by=norm_by)
        elif close and kwargs:
            self.compose(**kwargs)
        else:
            pass

    def query(self, Q: np.ndarray, norm_by: float=1.) -> np.ndarray:
        """Find document associations for a query.

        A query is a num_term-length (self.n) array of 0s and 1s. 1 means a
        term has been selected, while 0 is a deselected term. The resultant
        associations are a num_doc-length (self.m) array of floats.

        This is equation 12 in Giuliano (1963).

        Parameters
        ----------
        Q
            The query vector
        norm_by
            Normalization (0, 1) for the Block

        Returns
        -------
        A
            Document association values for the query
        """
        # Validate the query and check whether we need to re-compose
        self._validate_query(Q)
        self._set_state(norm_by)

        # Decompose the Block and build the components of the equation
        E, C, B, D = self.decompose()
        facA = inv(self.Idoc - E) @ (C @ inv(self.Iterm - D))
        facB = inv(
            self.Iterm - (B @ inv(self.Idoc - E)) @ (C @ inv(self.Iterm - D))
        )

        # Re-compose the Block from the initializing data if we're working with
        # a different `norm_by` than the initializing one
        if not np.isclose(self.norm_by, norm_by):
            self.compose()

        return facA @ facB @ Q

    def query_DTM(self, Q: np.ndarray, norm_by: float=1.) -> np.ndarray:
        """Query document associations assuming no information about term-term
        or document-document interaction is available.

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
        # Validate the query. Then, since we're discounting any information
        # we'd otherwise gain from the document-document and term-term
        # matrices, set the state with zeroed-out versions of them
        self._validate_query(Q)
        self._set_state(
            E=np.zeros_like(self.E)
            , D=np.zeros_like(self.D)
            , norm_by=norm_by
        )

        # Decompose the Block and build the pieces of the equation
        E, C, B, D = self.decompose()

        facA = C @ inv(self.Iterm - (B @ C))

        # Re-compose the Block from the initializing data
        self.compose()

        return facA @ Q

    def word_associations(self) -> np.ndarray:
        """Find word-word associations in a Block.

        This is discussed after equation 12 in Giuliano (1963, 230).

        Returns
        -------
        A
            Word associations
        """
        # Decompose the Block and build the components of the equation
        E, C, B, D = self.decompose()
        facA = inv(self.Iterm - D)
        facB = inv(
            self.Iterm - ((B @ inv(self.Idoc - E)) @ (C @ inv(self.Iterm - D)))
        )

        return facA @ facB

    def document_associations(self) -> np.ndarray:
        """Find document-document associations in a Block.

        This is discussed after equation 12 in Giuliano (1963, 230).

        Returns
        -------
        A
            Document associations
        """
        # Decompose the Block and retrieve the document-document matrix
        E, *_ = self.decompose()
        
        return inv(self.Idoc - E)
