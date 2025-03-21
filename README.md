# scienzaexpress.preflights

A collection of "preflight" checks for Scienza Express's RISE CMS.

## Features

These actions/views are available in any folder:
- Valida PDF - immagini

  Controlla che i raster inclusi nei PDF abbiano risoluzione suffiente. Controlla tutti i PDF della cartella su cui viene eseguito.

- Valida PDF - metadata

  Controlla che tutti i metadata necessari siano presenti nelle pagine appropriate. Ha bisogno che di un "Production Metadata" (lo cerca nelle cartelle "XML" contigue o superiori alla cartella su cui viene eseguito. Controlla tutti i PDF della cartella su cui viene eseguito.

- Genera XML per ISBN

  Genera un file XML per ISBN. Ha bisogno che di un "Production Metadata" (lo cerca nelle cartelle "XML" contigue o superiori alla cartella su cui viene eseguito. Sovrascrive eventuali file dello stesso tipo presenti.

- Genera XML app-ready

  Come sopra, in un formato leggermente diverso.

A content type called "Production Metadata" is also available. It stores metadata for RISE objects and is used by some of th

## Installation

Add to buildout or, if using `pip`, just run `pip install .../scienzaexpress.preflights`

Restart your instance, visit the add-on admin page and install the product.
